from elaspic_rest_api import jobsubmitter as js
import pytest

@pytest.mark.asyncio
async def test_query_mutation_data():
    item = js.Item(
        run_type="mutations",
        args={"job_id": 1, "job_type": "local", "protein_id": "d822d7", "mutations": "P37A"},
    )
    values = await js.elaspic2.query_mutation_data(item)
    print(values)
