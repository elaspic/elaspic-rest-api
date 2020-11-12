import asyncio
import logging
from typing import Dict

import aiomysql

from elaspic_rest_api import config

logger = logging.getLogger(__name__)


class _DBConnection:
    db_name: str
    db_connection_params: Dict
    pools: Dict[str, int] = {}

    def __init__(self):
        self._conn = None

    async def __aenter__(self):
        # Some tests will fail if we do not have a different pool for each asyncio loop
        loop = asyncio.get_running_loop()
        key = (self.db_name, hash(loop))

        try:
            pool = self.pools[key]
        except KeyError:
            pool = await aiomysql.create_pool(
                db=self.db_name, loop=loop, **self.db_connection_params
            )
            self.pools[key] = pool

        self._conn = await pool.acquire()
        return self._conn

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._conn.close()


class EDBConnection(_DBConnection):
    db_name = config.DB_NAME_ELASPIC
    db_connection_params = config.DB_CONNECTION_PARAMS


class WDBConnection(_DBConnection):
    db_name = config.DB_NAME_WEBSERVER
    db_connection_params = config.DB_CONNECTION_PARAMS
