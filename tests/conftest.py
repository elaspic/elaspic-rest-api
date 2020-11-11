from pathlib import Path

import pytest
import yaml

DATA_DIR = Path(__file__).parent.joinpath("data").resolve(strict=True)

with DATA_DIR.joinpath("testcases.yaml").open() as fin:
    DATA_IN = yaml.load(fin.read(), Loader=yaml.FullLoader)


@pytest.fixture(scope="function", params=DATA_IN)
def data_in(request):
    return request.param.copy()
