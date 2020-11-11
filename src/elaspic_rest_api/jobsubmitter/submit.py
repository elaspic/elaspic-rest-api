import asyncio
import logging
import os
import re
import shlex
import time
from asyncio import Queue
from textwrap import dedent
from typing import Dict

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js

logger = logging.getLogger(__name__)

JOB_ID_RE = re.compile(r"^Submitted batch job (\d+)$")

QSUB_OPTIONS = {
    "sequence": {
        "elaspic_run_type": 1,
        "num_cores": 1,
        "time": "24:00:00",
        "mem": "24G",
    },
    "model": {
        "elaspic_run_type": 2,
        "num_cores": 1,
        "time": "24:00:00",
        "mem": "24G",
    },
    "mutations": {
        "elaspic_run_type": 3,
        "num_cores": 1,
        "time": "24:00:00",
        "mem": "12G",
    },
}


def create_qsub_system_command(item: js.Item) -> str:
    qsub_options = QSUB_OPTIONS[item.run_type]
    system_command = dedent(
        f"""\
        ssh {config.SLURM_MASTER_USER}@{config.SLURM_MASTER_HOST}
        DB_NAME_ELASPIC="{config.DB_NAME_ELASPIC}"
        DB_NAME_WEBSERVER="{config.DB_NAME_WEBSERVER}"
        DB_HOST="{config.DB_HOST}"
        DB_PORT="{config.DB_PORT}"
        DB_USER="{config.DB_USER}"
        DB_PASSWORD="{config.DB_PASSWORD}"
        lock_filename="{item.lock_path}"
        lock_filename_finished="{item.finished_lock_path}"
        protein_id="{item.args['protein_id']}"
        mutations="{item.args['mutations']}"
        uniprot_domain_pair_ids="{item.args['uniprot_domain_pair_ids']}"
        structure_file="{item.args['structure_file'] or ''}"
        sequence_file="{item.args['sequence_file'] or ''}"
        SCRIPTS_DIR="{config.SCRIPTS_DIR}"
        ELASPIC_VERSION="{config.ELASPIC_VERSION}"
        run_type={item.run_type}
        elaspic_run_type={qsub_options["elaspic_run_type"]}
        sbatch
        --time={qsub_options["time"]}
        --nodes=1
        --ntasks-per-node={qsub_options["num_cores"]}
        --mem={qsub_options["mem"]}
        "{config.SCRIPTS_DIR}/{item.args['job_type']}.sh"
        """
    ).replace("\n", " ")
    return system_command


async def pre_qsub(
    pre_qsub_queue: Queue, qsub_queue: Queue, precalculated: Dict, precalculated_cache: Dict
) -> None:
    """Wait while the sequence and model prerequisites are being calculated."""
    while True:
        for _ in range(pre_qsub_queue.qsize()):
            logger.debug("pre_qsub")
            item = await pre_qsub_queue.get()
            have_prereqs = js.check_prereqs(item.prereqs, precalculated, precalculated_cache)
            if not have_prereqs:
                logger.debug("Waiting for prereqs: {}".format(item.prereqs))
                restarting = abs(time.time() - item.init_time) < js.perf.JOB_TIMEOUT
                if restarting:
                    await pre_qsub_queue.put(item)
                else:
                    await js.set_db_errors([item])
            else:
                await qsub_queue.put(item)
            await asyncio.sleep(js.perf.SLEEP_FOR_LOOP)
        await asyncio.sleep(js.perf.SLEEP_FOR_QSTAT)


async def qsub(
    qsub_queue: Queue, validation_queue: Queue, precalculated: Dict, precalculated_cache: Dict
) -> None:
    """Submit jobs."""
    while True:
        item = await qsub_queue.get()

        if item.run_type in ["sequence", "model"] and (
            item.unique_id in precalculated_cache or item.unique_id in precalculated
        ):
            logger.debug("Item '{}' already calculated. Skipping...".format(item.unique_id))
            continue

        try:
            open(item.lock_path, "x").close()
        except FileExistsError:
            logger.debug("Item '%s' already being calculated. Skipping...", item.unique_id)
            continue

        try:
            system_command = create_qsub_system_command(item)
            logger.debug("Running system command: %s", system_command)
            proc = await asyncio.create_subprocess_exec(
                *shlex.split(system_command),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            result_bytes, error_message_bytes = await proc.communicate()
            result = result_bytes.decode()
            error_message = error_message_bytes.decode()
            job_ids = JOB_ID_RE.findall(result)
            logger.debug("job_id: %s", job_ids)

            if not job_ids:
                restart_or_drop(item, qsub_queue, system_command, result, error_message)
                continue

            try:
                job_id = job_ids[0]
            except ValueError:
                restart_or_drop(item, qsub_queue, system_command, result, error_message)
                continue

            item.set_job_id(job_id)
            await validation_queue.put(item)
        except Exception as e:
            try:
                os.remove(item.lock_path)
            except FileNotFoundError:
                pass
            await asyncio.sleep(js.perf.SLEEP_FOR_ERROR)
            restart_or_drop(item, qsub_queue, error_message=str(e))
        #
        await asyncio.sleep(js.perf.SLEEP_FOR_QSUB)


async def restart_or_drop(
    item: js.Item, qsub_queue: Queue, system_command: str = "unk", result="unk", error_message="unk"
) -> None:
    restarting = item.qsub_tries < 5
    restarting_msg = " Restarting..." if restarting else "Too many restarts. Skipping..."
    logger.error(
        "Submitting job with system command '%s' produced no job id and the following "
        "results: '%s' and error: '%s'. %s",
        system_command,
        result,
        error_message,
        restarting_msg,
    )
    if restarting:
        item.qsub_tries += 1
        await qsub_queue.put(item)
    else:
        await js.set_db_errors([item])
