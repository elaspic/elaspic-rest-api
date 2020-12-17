import logging
import time
from asyncio import Queue
from textwrap import dedent
from typing import Dict

import aiofiles

from elaspic_rest_api import jobsubmitter as js

logger = logging.getLogger(__name__)


async def restart_or_drop(
    item: js.Item,
    ds: js.DataStructures,
    system_command: str = "unk",
    result="unk",
    error_message="unk",
) -> None:
    restarting = item.qsub_tries < 5 and (
        item.start_time is None or abs(time.time() - item.start_time) < js.perf.JOB_TIMEOUT
    )
    logger.error(
        (
            "Error runing job '%s'. Num squb retries: %s. "
            "System command: '%s'. Result: %s. Error message: %s. Restarting: %s."
        ),
        item.unique_id,
        item.qsub_tries,
        system_command,
        result,
        error_message,
        "Restarting..." if restarting else "Too many restarts. Skipping...",
    )
    js.email.send_admin_email(item, system_command, restarting)

    try:
        await aiofiles.os.remove(item.lock_path)
    except FileNotFoundError:
        pass

    if restarting:
        item.qsub_tries += 1
        await ds.qsub_queue.put(item)
    else:
        await remove_from_monitored(item, ds.monitored_jobs)
        await set_db_errors([item])


async def set_db_errors(error_queue):
    async def helper(cur, item):
        job_id = item.args["job_id"]
        protein_id = item.args["protein_id"]
        mut = item.args.get("mutations", "%")
        db_command = dedent(
            """\
            UPDATE muts
            JOIN job_to_mut ON (job_to_mut.mut_id = muts.id)
            JOIN jobs ON (jobs.jobID = job_to_mut.job_id)
            SET muts.status = 'error'
            WHERE jobs.jobID = %s
            AND muts.protein = %s
            AND muts.mut = %s
            """
        )
        await cur.execute(db_command, (job_id, protein_id, mut))

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
                    "The following error occured while trying to send errors to the database:\n%s",
                    e,
                )


async def remove_from_monitored(item: js.Item, monitored_jobs: Dict):
    if item.args.get("webserver_job_id"):
        job_key = (item.args.get("webserver_job_id"), item.args.get("webserver_job_email"))
        logger.debug(
            "Removing unique_id '%s' from monitored_jobs with key '%s...", item.unique_id, job_key
        )
        try:
            monitored_jobs[job_key].remove(item.unique_id)
            logger.debug("Removed!")
        except KeyError:
            logger.debug("Key does not exist!")
