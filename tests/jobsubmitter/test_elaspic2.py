from pathlib import Path

import pytest

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.jobsubmitter.elaspic2 import COI


@pytest.mark.asyncio
async def test_query_mutation_data_local():
    item = js.Item(
        run_type="mutations",
        args={"job_id": 1, "job_type": "local", "protein_id": "d822d7", "mutations": "P37A"},
    )
    mutation_info_list = await js.elaspic2.query_mutation_data(item)
    assert len(mutation_info_list) >= 2
    for idx, mutation_info in enumerate(mutation_info_list):
        if idx == 0:
            assert mutation_info.coi == COI.CORE
        else:
            assert mutation_info.coi == COI.INTERFACE
        assert Path(config.DATA_DIR).joinpath(mutation_info.structure_file).is_file()


@pytest.mark.asyncio
async def test_query_mutation_data_database():
    item = js.Item(
        run_type="mutations",
        args={
            "job_id": "4a21dd",
            "job_type": "database",
            "protein_id": "O00522",
            "mutations": "E567Q",
        },
    )
    mutation_info_list = await js.elaspic2.query_mutation_data(item)
    assert len(mutation_info_list) >= 2
    for idx, mutation_info in enumerate(mutation_info_list):
        if idx == 0:
            assert mutation_info.coi == COI.CORE
        else:
            assert mutation_info.coi == COI.INTERFACE
        assert Path(config.DATA_DIR).joinpath(mutation_info.structure_file).is_file()
