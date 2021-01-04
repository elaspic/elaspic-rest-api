import asyncio
import logging
import shlex
from asyncio import Queue
from typing import Dict, Set

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js

logger = logging.getLogger(__name__)


async def finalize_finished_submissions_loop(monitored_jobs: Dict[js.JobKey, Set]):
    """Send "job complete" emails and clear `monitored_jobs` of finished jobs."""
    loop = asyncio.get_running_loop()
    while True:
        logger.debug("finalize_finished_submissions_loop")
        logger.debug("monitored_jobs: %s", monitored_jobs)
        if monitored_jobs:
            finished_jobs = []
            for job_key, job_set in list(monitored_jobs.items()):
                if not job_set:
                    logger.debug(
                        "monitored_jobs with key '%s' is empty, finalizing...", monitored_jobs
                    )
                    if job_key[1]:  # job email was specified
                        loop.run_in_executor(
                            None,
                            js.email.send_job_finished_email,
                            job_key[0],
                            job_key[1],
                            "complete",
                        )
                    await set_job_status(job_key[0])
                    finished_jobs.append(job_key)
                    await asyncio.sleep(js.perf.SLEEP_FOR_LOOP)
            for job_key in finished_jobs:
                monitored_jobs.pop(job_key)
        await asyncio.sleep(js.perf.SLEEP_FOR_QSTAT)


async def set_job_status(job_id: str) -> int:
    """Mark job with the specified `job_id` as "done"."""
    async with js.WDBConnection() as conn:
        async with conn.cursor() as cur:
            num_rows_affected = await cur.execute(FINALIZE_SUBMISSION_SQL, (job_id,))
        await conn.commit()
    return num_rows_affected


async def finalize_mutation(item: js.Item):
    """Mark mutations associated with a given `item` as "done" or "error"."""
    args = item.args
    async with js.WDBConnection() as conn:
        async with conn.cursor() as cur:
            for mutation in args["mutations"].split(","):
                # Local pipelines may have underscore in mutation
                if "_" in mutation:
                    mutation = mutation.split("_")[-1]
                await cur.execute(
                    FINALIZE_MUTATION_SQL, {"protein_id": args["protein_id"], "mutation": mutation}
                )
        await conn.commit()
    system_command = f'bash -c "rm -f "{config.DATA_DIR}/locks/*/*.lock""'
    await asyncio.create_subprocess_exec(*shlex.split(system_command))


async def set_db_errors(error_queue):
    async def helper(cur, item: js.Item):
        job_id = item.args["job_id"]
        protein_id = item.args["protein_id"]
        mutation = item.args.get("mutations", "%")
        if "_" in mutation:
            mutation = mutation.split("_")[-1]
        await cur.execute(SET_MUTATION_ERROR_SQL, (job_id, protein_id, mutation))

    async with js.WDBConnection() as conn:
        async with conn.cursor() as cur:
            try:
                if isinstance(error_queue, Queue):
                    while not error_queue.empty():
                        item = await error_queue.get()
                        await helper(cur, item)
                        logger.debug("set_db_errors for item %s", item)
                else:
                    for item in error_queue:
                        await helper(cur, item)
                        logger.debug("set_db_errors for item %s", item)
                await conn.commit()
            except Exception as e:
                logger.error(
                    "The following error occured while trying to send errors to the database: %s",
                    e,
                )


async def finalize_lingering_jobs(ds: js.DataStructures) -> None:
    await js.set_db_errors(ds.pre_qsub_queue)
    await js.set_db_errors(ds.qsub_queue)
    await js.set_db_errors(ds.validation_queue)
    system_command = f'bash -c "rm -f "{config.DATA_DIR}/locks/*/*.lock""'
    await asyncio.create_subprocess_exec(*shlex.split(system_command))


FINALIZE_SUBMISSION_SQL = """\
UPDATE jobs
SET isDone = 1, dateFinished = now()
WHERE jobID = %s;
"""

SET_MUTATION_ERROR_SQL = """\
UPDATE muts
JOIN job_to_mut ON (job_to_mut.mut_id = muts.id)
JOIN jobs ON (jobs.jobID = job_to_mut.job_id)
SET muts.status = 'error'
WHERE jobs.jobID = %s
AND muts.protein = %s
AND muts.mut = %s
"""

FINALIZE_MUTATION_SQL = """\
LOCK TABLES muts AS web_muts WRITE,
            elaspic_core_mutation AS ecm READ,
            elaspic_core_mutation_local AS ecml READ,
            elaspic_interface_mutation AS eim READ,
            elaspic_interface_mutation_local eiml READ;

UPDATE muts web_muts
LEFT JOIN elaspic_core_mutation ecm ON (
    web_muts.protein = ecm.protein_id and web_muts.mut = ecm.mutation)
LEFT JOIN elaspic_core_mutation_local ecml ON (
    web_muts.protein = ecml.protein_id and web_muts.mut = ecml.mutation)
SET web_muts.affectedType='CO', web_muts.status='error', web_muts.dateFinished = now(),
    web_muts.error='1: ddG not calculated'
WHERE web_muts.protein = %(protein_id)s and web_muts.mut = %(mutation)s AND
      ecm.ddg IS NULL AND ecml.ddg IS NULL;

UPDATE muts web_muts
LEFT JOIN elaspic_core_mutation ecm ON (
    web_muts.protein = ecm.protein_id and web_muts.mut = ecm.mutation)
LEFT JOIN elaspic_core_mutation_local ecml ON (
    web_muts.protein = ecml.protein_id and web_muts.mut = ecml.mutation)
SET web_muts.affectedType='CO', web_muts.status='done', web_muts.dateFinished = now(),
    web_muts.error=Null
WHERE web_muts.protein = %(protein_id)s and web_muts.mut = %(mutation)s AND
    (ecm.ddg IS NOT NULL OR ecml.ddg IS NOT NULL);

UPDATE muts web_muts
LEFT JOIN elaspic_interface_mutation eim ON (
    web_muts.protein = eim.protein_id and web_muts.mut = eim.mutation)
LEFT JOIN elaspic_interface_mutation_local eiml ON (
    web_muts.protein = eiml.protein_id and web_muts.mut = eiml.mutation)
SET web_muts.affectedType='IN', web_muts.status='done', web_muts.dateFinished = now(),
    web_muts.error=Null
WHERE web_muts.protein = %(protein_id)s and web_muts.mut = %(mutation)s AND
    (eim.ddg IS NOT NULL OR eiml.ddg IS NOT NULL);

UNLOCK TABLES;
"""
