import logging
import time
from typing import Dict

import aiofiles

from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.finalize import set_db_errors

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
    if not restarting:
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
