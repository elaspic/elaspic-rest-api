from unittest.mock import patch
from urllib.parse import urljoin

import pytest

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.jobsubmitter.elaspic2types import COI, MutationInfo
from elaspic_rest_api.utils import mock_await, return_on_call


@pytest.mark.asyncio
@patch("elaspic_rest_api.jobsubmitter.elaspic2.aiohttp.ClientSession.delete", mock_await)
@patch("elaspic_rest_api.jobsubmitter.elaspic2.js.remove_from_monitored", mock_await)
@patch("elaspic_rest_api.jobsubmitter.elaspic2.js.finalize_mutation", mock_await)
@patch("elaspic_rest_api.jobsubmitter.elaspic2.update_mutation_scores")
async def test_elaspic2_collect_loop(mock_update_mutation_scores):
    el2_web_url = urljoin(config.ELASPIC2_URL, "/jobs/229764931")

    mutation_info_list = [
        MutationInfo(
            1,
            structure_file="1MFG.pdb",
            chain_id="A",
            mutation="G1A",
            protein_id="1mfg-local",
            coi=COI.CORE,
            el2_web_url=el2_web_url,
        ),
        MutationInfo(
            1,
            structure_file="1MFG.pdb",
            chain_id="A",
            mutation="G1A",
            protein_id="1mfg-local",
            coi=COI.INTERFACE,
            el2_web_url=el2_web_url,
        ),
    ]

    mutation_info_wscores_list = [
        mutation_info_list[0]._replace(
            protbert_score=0.011648587882518768,
            proteinsolver_score=0.7335909865796566,
            el2_score=0.3672627929817027,
        ),
        mutation_info_list[1]._replace(
            protbert_score=0.019379954785108566,
            proteinsolver_score=0.6837433353066444,
            el2_score=-0.969817502829359,
        ),
    ]

    item = js.Item(
        run_type="mutations",
        args={
            "job_id": "unk",
            "job_type": "database",
            "protein_id": "XXX",
            "mutations": "G1A,G1C",
        },
    )
    item.el2_mutation_info_list.extend(mutation_info_list)

    ds = js.DataStructures()
    await ds.elaspic2_running_queue.put(item)

    with return_on_call("elaspic_rest_api.jobsubmitter.elaspic2.asyncio.sleep"):
        await js.elaspic2_collect_loop(ds)

    mock_update_mutation_scores.assert_called_once_with(
        item.args["job_type"], mutation_info_wscores_list
    )
