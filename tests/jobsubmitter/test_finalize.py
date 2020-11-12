import pytest

from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.jobsubmitter.finalize import set_job_status

@pytest.mark.asyncio
async def test_set_job_status_valid():
    job_id = "000261"
    num_rows_affected = await set_job_status(job_id)
    assert num_rows_affected == 1


@pytest.mark.asyncio
async def test_set_job_status_invalid():
    job_id = "9999999999"
    num_rows_affected = await set_job_status(job_id)
    assert num_rows_affected == 0


@pytest.mark.asyncio
async def test_finalize_mutation(data_in):
    items_list = js.parse_input_data(data_in)
    for items in items_list:
        s, m, muts = items
        for item in muts:
            js.finalize_mutation(item)
