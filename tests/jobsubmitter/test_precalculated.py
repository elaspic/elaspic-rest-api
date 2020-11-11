import pytest

from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.utils import return_on_call


@pytest.mark.asyncio
async def test_check_prereqs_true():
    prereq = ["database.model.956a8e"]
    precalculated = {"database.model.956a8e": 3880078}
    precalculated_cache = {"database.model.68b8fe": 3880076, "local.model.7a2dd6": 7625616}

    is_precalculated = js.check_prereqs(prereq, precalculated, precalculated_cache)
    assert is_precalculated


@pytest.mark.asyncio
async def test_check_prereqs_false():
    prereq = ["database.model.xoxo"]
    precalculated = {"database.model.956a8e": 3880078}
    precalculated_cache = {"database.model.68b8fe": 3880076, "local.model.7a2dd6": 7625616}

    is_precalculated = js.check_prereqs(prereq, precalculated, precalculated_cache)
    assert not is_precalculated


@pytest.mark.asyncio
async def test_update_precalculated():
    precalculated = {}
    await js.update_precalculated(precalculated)
    assert len(precalculated) > 0


@pytest.mark.asyncio
async def test_persist_precalculated():
    precalculated_ref = {"database.model.956a8e": 3880078}
    precalculated_cache_ref = {"database.model.68b8fe": 3880076, "local.model.7a2dd6": 7625616}

    precalculated = precalculated_ref.copy()
    precalculated_cache = precalculated_cache_ref.copy()

    with return_on_call("elaspic_rest_api.jobsubmitter.precalculated.asyncio.sleep"):
        await js.persist_precalculated(precalculated, precalculated_cache)

    assert precalculated == {**precalculated_ref, **precalculated_cache_ref}
    assert not precalculated_cache
