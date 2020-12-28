import asyncio
import os
from pathlib import Path
from typing import Dict
from unittest.mock import patch

import pytest

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.jobsubmitter.elaspic2 import extract_protein_info, resolve_mutation_info
from elaspic_rest_api.jobsubmitter.elaspic2db import get_mutation_info, update_mutation_scores
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


def log_to_exception(*args) -> None:
    raise Exception(args[0] % args[1:])


@patch("elaspic_rest_api.jobsubmitter.elaspic2db.logger.error", log_to_exception)
@pytest.mark.asyncio
async def test_update_mutation_scores_local(data_dir: Path):
    reference = [
        MutationInfo(
            domain_or_interface_id=11750,
            structure_file="unused/mdm2-peptide/inputA_0--G33A/inputA_0--G33A-wt.pdb",
            chain_id="A",
            mutation="G33A",
            protein_id="mdm2-peptide",
            coi=COI.CORE,
            el2_web_url="https://elaspic2-api.proteinsolver.org/jobs/234899688/",
        ),
        MutationInfo(
            domain_or_interface_id=4882,
            structure_file="unused/mdm2-peptide/inputA_0-inputB_1-G33A/inputA_0-inputB_1-G33A-wt.pdb",
            chain_id="A",
            mutation="G33A",
            protein_id="mdm2-peptide",
            coi=COI.INTERFACE,
            el2_web_url="https://elaspic2-api.proteinsolver.org/jobs/234899717/",
        )
    ]
    mutation_info_list = [
        # First set everything to 0
        reference[0]._replace(
            protbert_score=0.0,
            proteinsolver_score=0.0,
            el2_score=0.0,
            el2_version="",
        ),
        reference[1]._replace(
            protbert_score=0.0,
            proteinsolver_score=0.0,
            el2_score=0.0,
            el2_version="0",
        ),
        # Then set everything back to actual values
        reference[0]._replace(
            protbert_score=0.007627921178936958,
            proteinsolver_score=0.14106684923171997,
            el2_score=0.020919730409294984,
            el2_version="0.1.13",
        ),
        reference[1]._replace(
            protbert_score=0.006903011351823807,
            proteinsolver_score=0.8102158680558205,
            el2_score=-0.4328730274441723,
            el2_version="0.1.13",
        ),
    ]

    await update_mutation_scores("local", mutation_info_list)
