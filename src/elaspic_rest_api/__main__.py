import logging

import fire

from elaspic_rest_api.utils import copy_scripts


class CLI:
    def __init__(self, log_level="info"):
        log_levels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        level = log_levels[log_level]
        logging.basicConfig(format="%(message)s", level=level)

    def copy_scripts(self):
        return copy_scripts()


if __name__ == "__main__":
    fire.Fire(CLI)
