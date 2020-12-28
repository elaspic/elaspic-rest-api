import asyncio
import os
from pathlib import Path
from typing import Dict
from unittest.mock import patch

import pytest

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.jobsubmitter.elaspic2 import extract_protein_info, resolve_mutation_info
from elaspic_rest_api.jobsubmitter.elaspic2db import get_mutation_info
from elaspic_rest_api.jobsubmitter.elaspic2types import COI, MutationInfo


@pytest.mark.parametrize("coi", list(COI))
def test_extract_protein_info(data_dir: Path, coi: COI):
    structure_file = data_dir.joinpath("structures", "1MFG.pdb").resolve(strict=True)
    mutation_info = MutationInfo(
        domain_or_interface_id=1,
        structure_file=structure_file.as_posix(),
        chain_id="B",
        mutation="E1A",
        protein_id="test-local",
        coi=coi,
    )

    class mock_config:
        SITE_URL = "http://elaspic.kimlab.org"
        DATA_DIR = data_dir.as_posix()
        SITE_DATA_DIR = DATA_DIR

    with patch("elaspic_rest_api.jobsubmitter.elaspic2.config", mock_config):
        protein_info = extract_protein_info(mutation_info)

    _validate_protein_info(protein_info, mutation_info)


def _validate_protein_info(protein_info: Dict, mutation_info: MutationInfo):
    assert (
        protein_info["protein_sequence"][int(protein_info["mutations"][1:-1]) - 1]
        == protein_info["mutations"][0]
    )

    if mutation_info.coi == COI.CORE:
        assert "ligand_sequence" not in protein_info
    else:
        assert protein_info["ligand_sequence"]


@pytest.mark.skipif("CI" in os.environ, reason="Test needs access to prod filesystem.")
@pytest.mark.asyncio
async def test_get_mutation_info_local():
    item = js.Item(
        run_type="mutations",
        args={"job_id": 1, "job_type": "local", "protein_id": "d822d7", "mutations": "P37A"},
    )
    loop = asyncio.get_running_loop()
    mutation_info_list = await get_mutation_info(item)
    mutation_info_list = await loop.run_in_executor(None, resolve_mutation_info, mutation_info_list)
    assert len(mutation_info_list) >= 2
    for idx, mutation_info in enumerate(mutation_info_list):
        assert Path(mutation_info.structure_file).is_file()
        if idx == 0:
            assert mutation_info.coi == COI.CORE
        else:
            assert mutation_info.coi == COI.INTERFACE
        protein_info = extract_protein_info(mutation_info)
        _validate_protein_info(protein_info, mutation_info)


@pytest.mark.skipif("CI" in os.environ, reason="Test needs access to prod filesystem.")
@pytest.mark.asyncio
async def test_get_mutation_info_database():
    item = js.Item(
        run_type="mutations",
        args={
            "job_id": "4a21dd",
            "job_type": "database",
            "protein_id": "O00522",
            "mutations": "E567Q",
        },
    )
    loop = asyncio.get_running_loop()
    mutation_info_list = await get_mutation_info(item)
    mutation_info_list = await loop.run_in_executor(None, resolve_mutation_info, mutation_info_list)
    assert len(mutation_info_list) >= 2
    for idx, mutation_info in enumerate(mutation_info_list):
        if idx == 0:
            assert mutation_info.coi == COI.CORE
        else:
            assert mutation_info.coi == COI.INTERFACE
        assert Path(config.DATA_DIR).joinpath(mutation_info.structure_file).is_file()
        protein_info = extract_protein_info(mutation_info)
        _validate_protein_info(protein_info, mutation_info)
