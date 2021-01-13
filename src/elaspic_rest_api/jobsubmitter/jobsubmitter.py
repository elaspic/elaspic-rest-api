import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Dict, List, Set, Tuple

from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.types import DataIn

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor()


async def start_jobsubmitter(ds: js.DataStructures) -> Dict[str, asyncio.Task]:
    task_fns = {
        "update_precalculated": partial(js.update_precalculated, ds.precalculated),
        "persist_precalculated": partial(
            js.persist_precalculated, ds.precalculated, ds.precalculated_cache
        ),
        "pre_qsub": partial(js.pre_qsub, ds),
        "qsub": partial(js.qsub, ds),
        "qstat": js.qstat,
        "validation": partial(js.validation, ds),
        "el2_submit": partial(js.elaspic2_submit_loop, ds),
        "el2_collect": partial(js.elaspic2_collect_loop, ds),
        "finalize_finished_submissions": partial(
            js.finalize_finished_submissions_loop, ds.monitored_jobs
        ),
    }

    tasks: Dict[str, asyncio.Task] = {}
    for task_name, task_fn in task_fns.items():
        if task_name not in tasks:
            logger.info("Creating task %s", task_name)
            tasks[task_name] = asyncio.create_task(task_fn(), name=task_name)

    try:
        await js.monitor_stats(ds, task_fns, tasks)
    except asyncio.CancelledError:
        for task in tasks.values():
            task.cancel()


async def submit_job(data_in: DataIn, ds: js.DataStructures):
    """
    Parameters
    ----------
    data_in : list of dicts
        Each dict should have the following elements:
        - job_id (all?)
        - job_type  (all)
        - job_emial (optional)
        - mutations
            - protein_id  (all)
            - structure_file  (local)
            - sequence_file  (local)
            - mutations  (all)
                Can be a comma-separated list of mutations, e.g. M1A,G2A
            - uniprot_domain_pair_ids  (database)
                Comma-separated list of uniprot_domain_pair_id interfaces to analyse.
    """
    logger.debug("")
    items_list = parse_input_data(data_in)
    for items in items_list:
        s, m, muts = items

        have_prereqs = True
        # Add sequence job
        if not js.check_prereqs([s.unique_id], ds.precalculated, ds.precalculated_cache):
            await ds.qsub_queue.put(s)
            have_prereqs = False
        # Add model job
        if not js.check_prereqs([m.unique_id], ds.precalculated, ds.precalculated_cache):
            await ds.qsub_queue.put(m)
            have_prereqs = False
        # Add mutation jobs
        job_mutations = set()
        for mut in muts:
            if have_prereqs:
                await ds.qsub_queue.put(mut)
            else:
                await ds.pre_qsub_queue.put(mut)
            job_mutations.add(mut.unique_id)
        # ELASPIC 2
        # TODO: WIP
        # Monitoring to send the final email
        if job_mutations and (job_id := mut.args.get("webserver_job_id")):
            job_key = js.JobKey(job_id, mut.args.get("webserver_job_email"))
            ds.monitored_jobs.setdefault(job_key, set()).update(job_mutations)


def parse_input_data(data_in: DataIn) -> List[Tuple[js.Item, js.Item, Set[js.Item]]]:
    items_list = []
    for data in data_in.mutations:
        args: js.Args = data.dict()  # type: ignore
        args["job_id"] = data_in.job_id
        args["job_email"] = data_in.job_email
        args["job_type"] = data_in.job_type
        validate_args(args)
        s = js.Item(run_type="sequence", args=args)
        m = js.Item(run_type="model", args=args)
        muts = set()
        for mutation in args["mutations"].split(","):
            args1 = args.copy()
            args1["mutations"] = mutation
            mut = js.Item(run_type="mutations", args=args1)
            muts.add(mut)
        items_list.append((s, m, muts))
    return items_list


def validate_args(args):
    logger.debug("validate_args(%s)", args)
    # Make sure the job_type is specified and fail gracefully if it isn't
    if "job_type" not in args:
        reason = "Don't know whether running a local or a database mutation. args:\n{}".format(args)
        # raise aiohttp.web.HTTPBadRequest(reason=reason)
        raise Exception(reason)
    #
    if "job_id" in args and "webserver_job_id" not in args:
        args["webserver_job_id"] = args["job_id"]
    if "job_email" in args and "webserver_job_email" not in args:
        args["webserver_job_email"] = args["job_email"]

    # Fill in defaults:
    args["sequence_file"] = args.get("sequence_file", None)
    args["uniprot_domain_pair_ids"] = args.get("uniprot_domain_pair_ids", "")
    # Make sure we have all the required arguments for the given job type
    if args["job_type"] == "local":
        local_opts = ["protein_id", "mutations", "structure_file", "sequence_file"]
        if not all(c in args for c in local_opts):
            reason = "Wrong arguments for '{}' jobtype:\n{}".format(args["job_type"], args)
            # raise aiohttp.web.HTTPBadRequest(reason=reason)
            raise Exception(reason)
    elif args["job_type"] == "database":
        database_opts = ["protein_id", "mutations", "uniprot_domain_pair_ids"]
        args["structure_file"] = args.get("structure_file", None)
        if not all(c in args for c in database_opts):
            reason = "Wrong arguments for '{}' jobtype:\n{}".format(args["job_type"], args)
            # raise aiohttp.web.HTTPBadRequest(reason=reason)
            raise Exception(reason)
    # This has been causing nothing but problems...
    #    # Sanitize our inputs
    #    valid_reg = re.compile(r'^[\w,_-@]+$')
    #    if not all(valid_reg.match(key) for key in args.keys()):
    #        logger.debug('Bad request keys')
    #        # raise aiohttp.web.HTTPBadRequest()
    #        raise Exception(reason)
    #    if not all(valid_reg.match(value) for value in args.values() if value):
    #        logger.debug('Bad request values')
    #        # raise aiohttp.web.HTTPBadRequest()
    #        raise Exception(reason)
