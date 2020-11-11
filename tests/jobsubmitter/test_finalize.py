import pytest

from elaspic_rest_api import jobsubmitter


@pytest.mark.asyncio
async def test_set_job_status_valid():
    job_id = "000261"
    num_rows_affected = await jobsubmitter.set_job_status(job_id)
    assert num_rows_affected == 1


@pytest.mark.asyncio
async def test_set_job_status_invalid():
    job_id = "9999999999"
    num_rows_affected = await jobsubmitter.set_job_status(job_id)
    assert num_rows_affected == 0
