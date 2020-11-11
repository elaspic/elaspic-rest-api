import importlib.resources
import logging
import os
import os.path as op
import shutil
from contextlib import contextmanager
from unittest.mock import patch

import elaspic_rest_api
from elaspic_rest_api import config

logger = logging.getLogger(__name__)


@contextmanager
def return_on_call(function_path: str):
    """Exit called process when function defined by "function_path" is called."""

    class CustomException(Exception):
        pass

    def return_on_call_(unused_duration):
        raise CustomException()

    with patch(function_path, return_on_call_):
        try:
            yield
        except CustomException:
            pass


def copy_scripts():
    os.makedirs(config.SCRIPTS_DIR, exist_ok=True)
    logger.info("Copying script files to remote ('%s')...", config.SCRIPTS_DIR)
    with importlib.resources.path(elaspic_rest_api, "scripts") as local_scripts_dir:
        for filename in os.listdir(local_scripts_dir):
            if op.isfile(op.join(local_scripts_dir, filename)):
                logger.debug(
                    "Copying '%s' to '%s'...",
                    op.join(local_scripts_dir, filename),
                    op.join(config.SCRIPTS_DIR, filename),
                )
                try:
                    shutil.copyfile(
                        op.join(local_scripts_dir, filename),
                        op.join(config.SCRIPTS_DIR, filename),
                    )
                except PermissionError as e:
                    logger.error(
                        "Do not have permission to copy file %s to %s!\n%s",
                        op.join(local_scripts_dir, filename),
                        op.join(config.SCRIPTS_DIR, filename),
                        e,
                    )
    logger.info("Done copying script files!")
