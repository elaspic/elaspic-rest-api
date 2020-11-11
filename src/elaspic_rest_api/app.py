import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

from elaspic_rest_api import config

if config.SENTRY_DSN:
    sentry_sdk.init(
        dsn="https://75ac5bde64ba45669cdbc39700edf502@o60259.ingest.sentry.io/5511660",
        integrations=[AioHttpIntegration()],
    )

import asyncio
import logging
import logging.config

from aiohttp import web

from elaspic_rest_api import config, jobsubmitter

logger = logging.getLogger(__name__)


async def generic_handler(request, request_type):
    """Handle GET and POST requests."""
    logger.debug("%s request: %s", request_type, request)

    # Parse input
    if request_type == "GET":
        data_in = dict(request.GET)
    elif request_type == "POST":
        data_in = await request.json()
    else:
        raise Exception("Wrong request_type: {}".format(request_type))
    logger.debug("data_in: {}".format(data_in))

    # Process input
    if data_in and data_in.get("secret_key") == config.SECRET_KEY:
        # Submit job
        muts = asyncio.ensure_future(jobsubmitter.main(data_in))
        logger.debug("muts: {}".format(muts))
        data_out = {"status": "submitted"}
    else:
        # Invalid request
        data_out = {"status": "error", "data_in": data_in}
    logger.debug("data_out:\n%s", data_out)

    # Response
    resp = web.json_response(data_out, status=200)
    logger.debug("resp:\n%s".resp)
    return resp


async def get(request):
    return await generic_handler(request, "GET")


async def post(request):
    return await generic_handler(request, "POST")


async def start_background_tasks(app):
    app["redis_listener"] = asyncio.create_task(listen_to_redis(app))


async def cleanup_background_tasks(app):
    for task in app["background_tasks"]:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    loop = asyncio.get_event_loop()
    data = app["background_data"]
    loop.run_until_complete(
        jobsubmitter.finalize_lingering_jobs(
            data.pre_qsub_queue, data.qsub_queue, data.validation_queue
        )
    )

    app["redis_listener"].cancel()
    await app["redis_listener"]


def main():
    app = web.Application()
    app.add_routes(
        [
            web.get("/elaspic/api/1.0/", get),
            web.post("/elaspic/api/1.0/", post),
        ]
    )
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    web.run_app(app)
