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
        self._current_pool = None
        self._current_conn = None

    async def __aenter__(self):
        # Some tests will fail if we do not have a different pool for each asyncio loop
        loop = asyncio.get_running_loop()
        key = (self.db_name, hash(loop))

        try:
            self._current_pool = self.pools[key]
        except KeyError:
            self._current_pool = await aiomysql.create_pool(
                db=self.db_name, loop=loop, maxsize=2, **self.db_connection_params
            )
            self.pools[key] = self._current_pool

        self._current_conn = await self._current_pool.acquire()
        return self._current_conn

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._current_pool.release(self._current_conn)


class EDBConnection(_DBConnection):
    db_name = config.DB_NAME_ELASPIC
    db_connection_params = config.DB_CONNECTION_PARAMS


class WDBConnection(_DBConnection):
    db_name = config.DB_NAME_WEBSERVER
    db_connection_params = config.DB_CONNECTION_PARAMS
