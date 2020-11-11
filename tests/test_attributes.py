import pytest

import elaspic_rest_api


@pytest.mark.parametrize("attribute", ["__version__"])
def test_attribute(attribute):
    assert getattr(elaspic_rest_api, attribute)


def test_main():
    import elaspic_rest_api

    assert elaspic_rest_api
