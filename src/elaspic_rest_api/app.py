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
of mutations on protein stability and protein interaction affinity.

Please see the source code repository for more information:
<https://gitlab.com/elaspic/elaspic-rest-api/>.
"""

app = FastAPI(
    title="ELASPIC REST API",
    description=description,
    version=elaspic_rest_api.__version__,
    root_path=config.ROOT_PATH,
)

js_data: Dict[str, Any] = {}


@app.post("/", status_code=200)
async def submit_job(data_in: DataIn, background_tasks: BackgroundTasks):
    if data_in.api_token == config.API_TOKEN:
        background_tasks.add_task(js.submit_job, data_in, js_data["ds"])
        return {"status": "submitted"}
    else:
        return {"status": "restricted"}


@app.get("/status", status_code=200)
async def get_pre_qsub_queue(api_token: str):
    queues_to_monitor = [
        "pre_qsub_queue",
        "qsub_queue",
        "validation_queue",
        "elaspic2_pending_queue",
        "elaspic2_running_queue",
    ]
    ds: js.DataStructures = js_data["ds"]
    if api_token == config.API_TOKEN:
        result = {
            **{name: list(getattr(ds, name)._queue) for name in queues_to_monitor},
            "monitored_jobs": [
                (tuple(key), list(values)) for key, values in ds.monitored_jobs.items()
            ],
        }
    else:
        result = {}
    return result


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
