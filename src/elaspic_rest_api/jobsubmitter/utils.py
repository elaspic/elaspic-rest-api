import logging
from asyncio import Queue
from textwrap import dedent
from typing import Dict

import aiomysql

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js

logger = logging.getLogger(__name__)


async def set_db_errors(error_queue):
    logger.debug("set_db_errors: {}".format(error_queue))

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

    async with aiomysql.connect(db=config.DB_NAME_WEBSERVER, **config.DB_CONNECTION_PARAMS) as conn:
        async with conn.cursor() as cur:
            try:
                if isinstance(error_queue, Queue):
                    while not error_queue.empty():
                        item = await error_queue.get()
                        await helper(cur, item)
                else:
                    for item in error_queue:
                        await helper(cur, item)
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
