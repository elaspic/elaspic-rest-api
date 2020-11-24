from pathlib import Path

import pytest
import yaml

from elaspic_rest_api import config
from elaspic_rest_api.types import DataIn

DATA_DIR = Path(__file__).parent.joinpath("data").resolve(strict=True)

with DATA_DIR.joinpath("testcases.yaml").open() as fin:
    DATA_IN = yaml.load(fin.read(), Loader=yaml.FullLoader)


@pytest.fixture
def data_dir():
    return DATA_DIR


@pytest.fixture(scope="function", params=DATA_IN)
def data_in(request):
    data = {"api_token": config.API_TOKEN, **request.param}
    return DataIn(**data)
