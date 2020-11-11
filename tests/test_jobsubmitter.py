import logging
import logging.config
from pathlib import Path

import pytest

from elaspic_rest_api import config, jobsubmitter

logger = logging.getLogger(__name__)
logger.debug("configured logging...")

JOB_OFFSET = 999000


@pytest.mark.asyncio
async def test_1(data_in):
    JOB_ID_OFFSET = 999000
    data_in["job_id"] += JOB_ID_OFFSET
    data_in["job_email"] = config.ADMIN_EMAIL
    data_in["secret_key"] = config.SECRET_KEY
    # Submit mutations
    mut = await jobsubmitter.main(data_in)
    logging.info("Submitted mutation: %s", mut)
    assert mut is None
    # Make sure jobs finish within a set ammount of time
    # started = datetime.datetime.now()
    # while not jobsubmitter.qsub_queue.empty():
    #     jobsubmitter._log_stats()
    #     elapsed = (datetime.datetime.now() - started).total_seconds()
    #     logger.debug("Running for %s seconds...", elapsed)
    #     if elapsed > 120:
    #         assert False, "Timeout!"
    #     await asyncio.sleep(10)
