import asyncio
import logging
import shlex
import time
from typing import Mapping, Set, Tuple

import aiofiles

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js

logger = logging.getLogger(__name__)

running_jobs_last_updated = 0.0
validation_last_updated = 0.0


async def show_stats(ds: js.DataStructures, tasks: Mapping[str, asyncio.Task]) -> None:
    while True:
        logger.info("*" * 50)
        logger.info("{:40}{:10}".format("Submitted jobs:", len(ds.running_jobs)))
        logger.info("{:40}{:10}".format("validation_queue:", ds.validation_queue.qsize()))
        logger.info("{:40}{:10}".format("qsub_queue:", ds.qsub_queue.qsize()))
        logger.info("{:40}{:10}".format("pre_qsub_queue:", ds.pre_qsub_queue.qsize()))
        # logger.debug('precalculated: {}'.format(precalculated))
        logger.info("precalculated_cache: {}".format(ds.precalculated_cache))
        for task_name, task in tasks.items():
            is_done = task.done()
            logger.info(
                "{:40}{:>10}".format(f"Task {task_name}:", "done" if is_done else "running")
            )
            if is_done:
                error = task.exception()
                if error is not None:
                    raise error
        logger.info("*" * 50)
        await asyncio.sleep(js.perf.SLEEP_FOR_INFO)


async def qstat(running_jobs: Set):
    global running_jobs_last_updated
    while True:
        logger.debug("squeue")
        system_command = (
            f"ssh {config.SLURM_MASTER_USER}@{config.SLURM_MASTER_HOST} "
            f"squeue -u '{config.SLURM_MASTER_USER}'"
        )
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(system_command),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        result_bytes, error_message = await proc.communicate()
        result = result_bytes.decode()
        if error_message:
            logger.error("system command: '%s', error message: '%s'", system_command, error_message)
            await asyncio.sleep(js.perf.SLEEP_FOR_ERROR)
            continue
        running_jobs.clear()
        running_jobs.update(
            {
                int(x.split(" ")[0])
                for x in [v.strip() for v in result.split("\n")]
                if x and x.split(" ")[0].isdigit()
            }
        )
        running_jobs_last_updated = time.time()
        await asyncio.sleep(js.perf.SLEEP_FOR_QSTAT)


async def validation(ds: js.DataStructures):
    """Validate finished jobs."""
    global validation_last_updated
    while True:
        for _ in range(ds.validation_queue.qsize()):
            logger.debug("validation")
            item = await ds.validation_queue.get()
            if (item.start_time > running_jobs_last_updated) or (item.job_id in ds.running_jobs):
                logger.debug("Job not ready for validation")
                await ds.validation_queue.put(item)
                await asyncio.sleep(js.perf.SLEEP_FOR_LOOP)
                continue
            #
            validation_passphrase = "Finished successfully"
            validated, system_command, result, error_message = await _validate_finished_item(
                item, validation_passphrase
            )
            if not validated:
                await js.restart_or_drop(item, ds, system_command, result, error_message)
                continue
            try:
                await aiofiles.os.remove(item.lock_path)
                logger.debug("Removed lock file for finished job %s", item.job_id)
            except FileNotFoundError:
                logger.debug(
                    "Failed to remove lock file for finished job %s (lock file: %s)",
                    item.job_id,
                    item.lock_path,
                )
            if item.run_type in ["sequence", "model"]:
                ds.precalculated_cache[item.unique_id] = item.job_id
                logger.debug("Added finished job %s to cache.", item.job_id)
            elif item.run_type in ["mutations"]:
                await ds.elaspic2_pending_queue.put(item)
            else:
                raise Exception(f"Invalid run type: {item.run_type}.")
            await asyncio.sleep(js.perf.SLEEP_FOR_LOOP)
        await asyncio.sleep(js.perf.SLEEP_FOR_QSTAT)


async def _validate_finished_item(
    item: js.Item, validation_passphrase: str
) -> Tuple[bool, str, str, str]:
    system_command = 'grep "{}" {}'.format(validation_passphrase, item.stdout_path)
    proc = await asyncio.create_subprocess_exec(
        *shlex.split(system_command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    result_bytes, error_message_bytes = await proc.communicate()
    result = result_bytes.decode()
    error_message = error_message_bytes.decode()
    validated = validation_passphrase in result
    return validated, system_command, result, error_message
