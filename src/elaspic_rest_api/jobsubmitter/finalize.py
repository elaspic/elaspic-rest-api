import asyncio
import logging
import shlex
from concurrent.futures import Executor
from textwrap import dedent
from typing import Dict, Set

import aiomysql

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js

logger = logging.getLogger(__name__)


async def finalize_finished_jobs(executor: Executor, monitored_jobs: Dict[js.JobKey, Set]):
    while True:
        logger.debug("finalize_finished_jobs")
        logger.debug("monitored_jobs: %s", monitored_jobs)
        if monitored_jobs:
            finished_jobs = []
            for job_key, job_set in monitored_jobs.items():
                if not job_set:
                    logger.debug(
                        "monitored_jobs with key '%s' is empty, finalizing...", monitored_jobs
                    )
                    if job_key[1]:  # job email was specified
                        executor.submit(
                            js.email.send_job_finished_email, job_key[0], job_key[1], "complete"
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
    async with aiomysql.connect(db=config.DB_NAME_WEBSERVER, **config.DB_CONNECTION_PARAMS) as conn:
        async with conn.cursor() as cur:
            db_command = dedent(
                """\
                UPDATE jobs
                SET isDone = 1, dateFinished = now()
                WHERE jobID = %s;
                """
            )
            num_rows_affected = await cur.execute(db_command, (job_id,))
        await conn.commit()
    return num_rows_affected


async def finalize_lingering_jobs(ds: js.DataStructures) -> None:
    await js.set_db_errors(ds.pre_qsub_queue)
    await js.set_db_errors(ds.qsub_queue)
    await js.set_db_errors(ds.validation_queue)
    system_command = f'bash -c "rm -f "{config.DATA_DIR}/locks/*/*.lock""'
    await asyncio.create_subprocess_exec(shlex.split(system_command))  # type: ignore
