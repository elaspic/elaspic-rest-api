import asyncio
import logging
from typing import Any, Dict

import sentry_sdk
from fastapi import BackgroundTasks, FastAPI
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

import elaspic_rest_api
from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.types import DataIn

logger = logging.getLogger(__name__)

description = """\
This page lists `ELASPIC` REST API endpoints that are available for evaluating the effect
of mutations on protein stability and protein interaction affinity.s
"""

app = FastAPI(
    title="ELASPIC REST API", description=description, version=elaspic_rest_api.__version__
)

js_data: Dict[str, Any] = {}


@app.post("/", status_code=200)
async def submit_job(data_in: DataIn, background_tasks: BackgroundTasks):
    if data_in.secret_key == config.SECRET_KEY:
        background_tasks.add_task(js.submit_job, data_in, js_data["ds"])
        return {"status": "submitted"}
    else:
        return {"status": "restricted"}


@app.get("/_ah/warmup", include_in_schema=False)
def warmup():
    return {}


@app.on_event("startup")
async def on_startup() -> None:
    js_data["ds"] = js.DataStructures()
    js_data["tasks"] = await js.start_jobsubmitter(js_data["ds"])


@app.on_event("shutdown")
async def on_shutdown() -> None:
    for task_name, task in js_data["tasks"].items():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await js.finalize_lingering_jobs(js_data["ds"])


if config.SENTRY_DSN:
    sentry_sdk.init(config.SENTRY_DSN, traces_sample_rate=1.0)
    app = SentryAsgiMiddleware(app)  # type: ignore
