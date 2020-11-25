import datetime
import os.path as op

import requests

from elaspic_rest_api import config

MAX_N = 10000
BATCH_SIZE = 100
DATA_OFFSET = 30000

REST_API_URL = "http://elaspic-rest-api:8080/"


with open(op.join(op.dirname(op.abspath(__file__)), "data", "cosmic_missing.tsv"), "r") as ifh:
    DATA = ifh.read().split("\n")


def test_one():
    d = DATA[0]
    data_in = {
        "job_id": "xoxoxo",
        "job_type": "database",
        "api_token": config.API_TOKEN,
        "mutations": [
            {
                "protein_id": d.split(".")[0],
                "mutations": d.split(".")[1],
                "uniprot_domain_pair_ids": "",
            }
        ],
    }
    r = requests.post(REST_API_URL, json=data_in)
    assert r.json().get("status") == "submitted"


def test_multi_mutants():
    """All mutations."""
    start_time = datetime.datetime.now()
    for i in range(DATA_OFFSET, DATA_OFFSET + MAX_N, BATCH_SIZE):
        data_in = {
            "job_id": "xoxoxo",
            "job_type": "database",
            "api_token": config.API_TOKEN,
            "mutations": [
                {
                    "protein_id": DATA[i + j].split(".")[0],
                    "mutations": DATA[i + j].split(".")[1],
                    "uniprot_domain_pair_ids": "",
                }
                for j in range(BATCH_SIZE)
            ],
        }
        r = requests.post(REST_API_URL, json=data_in)
        assert r.json().get("status") == "submitted"
    end_time = datetime.datetime.now()
    assert (end_time - start_time).total_seconds() / MAX_N < 0.1, "More than 100 ms per job!!!"
