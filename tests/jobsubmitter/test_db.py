from elaspic_rest_api.jobsubmitter import db
import pytest


@pytest.mark.parametrize("DBConnection", [db.EDBConnection, db.WDBConnection])
async def test_db(DBConnection):
    async with DBConnection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 42;")
            (r,) = await cur.fetchone()
            assert r == 42
