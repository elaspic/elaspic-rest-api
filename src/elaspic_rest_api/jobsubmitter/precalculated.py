import asyncio
import logging
from collections import deque
from typing import Dict

from elaspic_rest_api import jobsubmitter as js

logger = logging.getLogger(__name__)


def check_prereqs(
    prereqs, precalculated: Dict, precalculated_cache: Dict, lsd=deque(maxlen=512)
) -> bool:
    for prereq in prereqs:
        if prereq in lsd:
            continue
        elif prereq in precalculated_cache or prereq in precalculated:
            lsd.appendleft(prereq)
            continue
        else:
            return False
    return True


async def update_precalculated(precalculated: Dict) -> None:
    async with js.EDBConnection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, job_id from jobsubmitter_cache;")
            values = await cur.fetchall()
            precalculated.clear()
            precalculated.update({v[0]: v[1] for v in values})


async def persist_precalculated(precalculated: Dict, precalculated_cache: Dict) -> None:
    while True:
        logger.debug("persist_precalculated")
        if not precalculated_cache:
            await asyncio.sleep(js.perf.SLEEP_FOR_DB)
            continue
        try:
            async with js.EDBConnection() as conn:
                async with conn.cursor() as cur:
                    await cur.executemany(
                        "INSERT INTO jobsubmitter_cache (id, job_id) values (%s,%s) "
                        "ON DUPLICATE KEY UPDATE job_id=job_id;",
                        list(precalculated_cache.items()),
                    )
                    await conn.commit()
                # Update global variables
                precalculated.update(precalculated_cache)
                precalculated_cache.clear()
        except Exception as e:
            error_message = (
                "The following error occured while trying to persist data "
                "to the database:\n{}".format(e)
            )
            logger.error(error_message)
            await asyncio.sleep(js.perf.SLEEP_FOR_ERROR)
            continue
        await asyncio.sleep(js.perf.SLEEP_FOR_DB)
