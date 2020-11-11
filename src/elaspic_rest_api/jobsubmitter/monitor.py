import asyncio
import logging
import os
import shlex
import time
from typing import Set

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js

logger = logging.getLogger(__name__)

running_jobs_last_updated = 0.0
validation_last_updated = 0.0


async def show_stats(ds: js.DataStructures) -> None:
    while True:
        logger.info("*" * 50)
        logger.info("{:40}{:10}".format("Submitted jobs:", len(ds.running_jobs)))
        logger.info("{:40}{:10}".format("validation_queue:", ds.validation_queue.qsize()))
        logger.info("{:40}{:10}".format("qsub_queue:", ds.qsub_queue.qsize()))
        logger.info("{:40}{:10}".format("pre_qsub_queue:", ds.pre_qsub_queue.qsize()))
        # logger.debug('precalculated: {}'.format(precalculated))
        logger.info("precalculated_cache: {}".format(ds.precalculated_cache))
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
            system_command = 'grep "{}" {}'.format(validation_passphrase, item.stdout_path)
            logger.debug(system_command)
            proc = await asyncio.create_subprocess_exec(
                *shlex.split(system_command),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            result_bytes, error_message_bytes = await proc.communicate()
            result = result_bytes.decode()
            error_message = error_message_bytes.decode()
            validated = validation_passphrase in result
            logger.debug("validated: {}".format(validated))
            if validated:
                if item.run_type in ["sequence", "model"]:
                    logger.debug("Adding finished job {} to cache...".format(item.job_id))
                    ds.precalculated_cache[item.unique_id] = item.job_id
                    logger.debug("precalculated_cache: {}".format(ds.precalculated_cache))
                message = "Making sure the lock file '{}' has been removed... ".format(
                    item.lock_path
                )
                try:
                    os.remove(item.lock_path)
                    logger.debug(message + "nope!")
                except FileNotFoundError:
                    logger.debug(message + "yup!")
                js.remove_from_monitored(item, ds.monitored_jobs)
            else:
                error_message = "Failed to validate with system command:\n{}".format(system_command)
                restarting = (item.validation_tries < 5) & (
                    abs(time.time() - item.start_time) < js.perf.JOB_TIMEOUT
                )
                js.email.send_admin_email(item, system_command, restarting)
                logger.debug("Removing the lock file...")
                try:
                    os.remove(item.lock_path)
                    logger.debug("nope!")
                except FileNotFoundError:
                    logger.debug("yup!")
                if restarting:
                    logger.error(error_message + " Restarting...")
                    item.validation_tries += 1
                    await ds.qsub_queue.put(item)
                else:
                    logger.error(error_message + " Out of time. Skipping...")
                    await js.remove_from_monitored(item, ds.monitored_jobs)
                    await js.set_db_errors([item])
            await asyncio.sleep(js.perf.SLEEP_FOR_LOOP)
        await asyncio.sleep(js.perf.SLEEP_FOR_QSTAT)
