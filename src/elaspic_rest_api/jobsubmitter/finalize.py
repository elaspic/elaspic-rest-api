import asyncio
import logging
import shlex
from typing import Dict, Set

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js

logger = logging.getLogger(__name__)


FINALIZE_SUBMISSION_SQL = """\
UPDATE jobs
SET isDone = 1, dateFinished = now()
WHERE jobID = %s;
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


async def finalize_mutation(item: js.Item):
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


async def finalize_finished_submissions(monitored_jobs: Dict[js.JobKey, Set]):
    loop = asyncio.get_running_loop()
    while True:
        logger.debug("finalize_finished_submissions")
        logger.debug("monitored_jobs: %s", monitored_jobs)
        if monitored_jobs:
            finished_jobs = []
            for job_key, job_set in monitored_jobs.items():
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
    """
    Copy-paste from web_pipeline.functions, so that I don't have to laod all database models.
    """
    async with js.WDBConnection() as conn:
        async with conn.cursor() as cur:
            num_rows_affected = await cur.execute(FINALIZE_SUBMISSION_SQL, (job_id,))
        await conn.commit()
    return num_rows_affected


async def finalize_lingering_jobs(ds: js.DataStructures) -> None:
    await js.set_db_errors(ds.pre_qsub_queue)
    await js.set_db_errors(ds.qsub_queue)
    await js.set_db_errors(ds.validation_queue)
    system_command = f'bash -c "rm -f "{config.DATA_DIR}/locks/*/*.lock""'
    await asyncio.create_subprocess_exec(shlex.split(system_command))  # type: ignore
