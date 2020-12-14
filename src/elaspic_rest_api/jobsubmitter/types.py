import os.path as op
import time
from asyncio import Queue
from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple, Optional, Set, TypedDict

from elaspic_rest_api import config
from elaspic_rest_api.jobsubmitter.elaspic2types import MutationInfo


class JobKey(NamedTuple):
    job_id: str
    job_email: Optional[str]


@dataclass
class DataStructures:
    # Data structures
    pre_qsub_queue: Queue = field(default_factory=Queue)
    qsub_queue: Queue = field(default_factory=Queue)
    validation_queue: Queue = field(default_factory=Queue)
    elaspic2_pending_queue: Queue = field(default_factory=Queue)
    elaspic2_running_queue: Queue = field(default_factory=Queue)

    #: Mutation jobs that are being monitored for completion
    #: {(job_id, job_email): {unique_id_1, unique_id_2, ...}}
    #: Example: {JobKey(job_id=7, job_email=None): {"database.mutations.P0A921.A243R", ...}}
    monitored_jobs: Dict[JobKey, Set] = field(default_factory=dict)

    #: Persisted precalculated data
    #: Mapping from `unique_id` to `job_id`
    #: Example: {'database.model.68b8fe': 3880076, 'local.model.7a2dd6': 7625616, ...}
    precalculated: Dict[str, int] = field(default_factory=dict)

    #: In-memory precalculated data (has not been persisted yet)
    #: Mapping from `unique_id` to `job_id`
    #: Example: {'database.model.68b8fe': 3880076, 'local.model.7a2dd6': 7625616, ...}
    precalculated_cache: Dict[str, int] = field(default_factory=dict)


class Args(TypedDict):
    job_id: int
    #: One of ["database", "local"]
    job_type: str
    job_email: Optional[str]
    protein_id: str
    mutations: str
    structure_file: Optional[str]
    sequence_file: Optional[str]
    uniprot_domain_pair_ids: Optional[str]
    webserver_job_id: Optional[str]
    webserver_job_email: Optional[str]


class Item:
    #: SLURM job id of the currently-running job
    job_id: Optional[int]

    init_time: float
    start_time: Optional[float]

    def __init__(self, run_type: str, args: Args) -> None:
        assert run_type in ["sequence", "model", "mutations"]
        self.run_type = run_type
        self.args = args
        self.init_time = time.time()
        #
        self.qsub_tries = 0
        self.unique_id = get_unique_id(run_type, args)
        self.lock_path = get_lock_path(run_type, args, finished=False)
        self.finished_lock_path = get_lock_path(run_type, args, finished=True)
        self.prereqs = []
        if run_type == "mutations":
            self.prereqs = [
                "{job_type}.sequence.{protein_id}".format(**args),
                "{job_type}.model.{protein_id}".format(**args),
            ]
        #
        self.job_id = None
        self.start_time = None
        self.stdout_path = None  # need_job_id
        self.stderr_path = None  # need job_id
        # ELASPIC2
        self.el2_mutation_info_list: List[MutationInfo] = []

    def set_job_id(self, job_id: int) -> None:
        self.job_id = job_id
        self.start_time = time.time()
        self.stdout_path, self.stderr_path = get_log_paths(
            self.args["job_type"], self.job_id, self.args["protein_id"]
        )

    def __str__(self) -> str:
        return f"{self.job_id} {self.unique_id} {self.qsub_tries}"


def get_unique_id(run_type: str, args: Args) -> str:
    unique_id = ".".join([args["job_type"], run_type, args["protein_id"]])
    if run_type == "mutations":
        unique_id += "." + args["mutations"]
    return unique_id


def get_lock_path(run_type: str, args: Args, finished: bool = False) -> str:
    """Get the name of the lock file for the given run_type."""
    if run_type == "sequence":
        lock_path = op.join(
            config.PROVEAN_LOCK_DIR,
            "finished" if finished else "",
            "{}.lock".format(args["protein_id"]),
        )
    elif run_type == "model":
        lock_path = op.join(
            config.MODEL_LOCK_DIR,
            "finished" if finished else "",
            "{}.lock".format(args["protein_id"]),
        )
    elif run_type == "mutations":
        lock_path = op.join(
            config.MUTATION_LOCK_DIR,
            "finished" if finished else "",
            "{}.{}.lock".format(args["protein_id"], args["mutations"]),
        )
    else:
        raise RuntimeError
    return lock_path


def get_log_paths(job_type: str, job_id: str, protein_id: str):
    if job_type == "database":
        # Database
        args = dict(data_dir=config.DATA_DIR, job_id=job_id)
        stdout_path = "{data_dir}/pbs-output/{job_id}.out".format(**args)
        stderr_path = "{data_dir}/pbs-output/{job_id}.err".format(**args)
    else:
        # Local
        args = dict(data_dir=config.DATA_DIR, protein_id=protein_id, job_id=job_id)
        stdout_path = "{data_dir}/user_input/{protein_id}/pbs-output/{job_id}.out".format(**args)
        stderr_path = "{data_dir}/user_input/{protein_id}/pbs-output/{job_id}.err".format(**args)
    return stdout_path, stderr_path
