import logging
import os.path as op
import shlex
import subprocess
import sys

import pytest

import elaspic_rest_api

logger = logging.getLogger(__name__)


LOCAL_SCRIPTS_DIR = op.join(elaspic_rest_api.__path__[0], "scripts")

# For using the main elaspic archive dir:
# USER_INPUT_DIR = op.join(config.DATA_DIR, 'user_input')
# For using the tests 'data' dir
USER_INPUT_DIR = op.join(op.dirname(op.abspath(__file__)), "data")

RUNFILE_TEMPLATE = f"""\
{USER_INPUT_DIR}/{{unique_id}}/.elaspic/{{json_file}}\
"""

SYSTEM_COMMAND_TEMPLATE = f"""\
{sys.executable} {LOCAL_SCRIPTS_DIR}/local.py -d {USER_INPUT_DIR}/{{unique_id}} \
-u {{unique_id}} -t {{run_type}} {{mutations}} \
"""

DATA_IN = [
    {"unique_id": "0bbeda", "mutations": "1_Q241W"},
]


@pytest.fixture(params=DATA_IN)
def args(request):
    return request.param


def test_sequence(args):
    run_type = "sequence"
    runfile = RUNFILE_TEMPLATE.format(
        unique_id=args["unique_id"], json_file="{}.json".format(run_type)
    )
    assert op.isfile(runfile)
    system_command = SYSTEM_COMMAND_TEMPLATE.format(
        unique_id=args["unique_id"], run_type=run_type, mutations=""
    )
    logger.debug(system_command)
    sp = subprocess.run(shlex.split(system_command), universal_newlines=True)
    sp.check_returncode()


def test_model(args):
    run_type = "model"
    runfile = RUNFILE_TEMPLATE.format(
        unique_id=args["unique_id"], json_file="{}.json".format(run_type)
    )
    assert op.isfile(runfile)
    system_command = SYSTEM_COMMAND_TEMPLATE.format(
        unique_id=args["unique_id"], run_type=run_type, mutations=""
    )
    logger.debug(system_command)
    sp = subprocess.run(
        shlex.split(system_command), universal_newlines=True, stderr=subprocess.PIPE
    )
    logger.debug(sp.stderr)
    sp.check_returncode()
    # assert "Cannot delete or update a parent row: a foreign key constraint fails" in sp.stderr


def test_mutations(args):
    run_type = "mutation"
    for mutation in args["mutations"].split(","):
        runfile = RUNFILE_TEMPLATE.format(
            unique_id=args["unique_id"], json_file="{}_{}.json".format(run_type, mutation)
        )
        assert op.isfile(runfile)
        system_command = SYSTEM_COMMAND_TEMPLATE.format(
            unique_id=args["unique_id"], run_type=run_type, mutations=" -m {}".format(mutation)
        )
        logger.debug(system_command)
        sp = subprocess.run(shlex.split(system_command), universal_newlines=True)
        sp.check_returncode()
