def test_pytest_asyncio_is_installed(event_loop):
    assert event_loop is not None
