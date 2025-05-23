#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of grommunio_exporter

__appname__ = "grommunio_exporter"
__author__ = "Orsiris de Jong"
__site__ = "https://www.github.com/netinvent/grommunio_exporter"
__description__ = "Grommunio Prometheus data exporter"
__copyright__ = "Copyright (C) 2024-2025 NetInvent"
__license__ = "GPL-3.0-only"
__build__ = "2024110801"


import sys
import os
import logging
from ofunctions.logger_utils import logger_get_logger
from pathlib import Path
from argparse import ArgumentParser
from grommunio_exporter.__debug__ import _DEBUG
from grommunio_exporter.configuration import load_config, get_default_config
from grommunio_exporter import metrics

logger = logger_get_logger(__appname__ + ".log", debug=_DEBUG)


def _main():
    global logger
    _DEV = os.environ.get("_DEV", False)

    parser = ArgumentParser(
        prog=f"{__appname__}",
        description="""Grommunio API Prometheus exporter\n
This program is distributed under the GNU General Public License and comes with ABSOLUTELY NO WARRANTY.\n
This is free software, and you are welcome to redistribute it under certain conditions; Please type --license for more info.""",
    )

    parser.add_argument(
        "--dev", action="store_true", help="Run with uvicorn in devel environment"
    )

    parser.add_argument(
        "-c",
        "--config-file",
        dest="config_file",
        type=str,
        default=None,
        required=False,
        help="Path to YAML configuration file",
    )
    args = parser.parse_args()

    if args.config_file:
        config_file = Path(args.config_file)
        if not config_file.exists():
            logger.critical(f"Cannot load config file {config_file}")
            sys.exit(1)

        config_dict = load_config(config_file)
        if not config_dict:
            logger.critical(f"Cannot load configuration file {config_file}")
            sys.exit(1)
    else:
        config_dict = get_default_config()

    try:
        logger = logger_get_logger(config_dict.g("http_server.log_file"), debug=_DEBUG)
    except (AttributeError, KeyError, IndexError, TypeError):
        pass

    if args.dev:
        _DEV = True

    try:
        listen = config_dict.g("http_server.listen")
    except (TypeError, KeyError, AttributeError):
        listen = None
    try:
        port = config_dict.g("http_server.port")
    except (TypeError, KeyError, AttributeError):
        port = None

    # Cannot use gunicorn on Windows
    if _DEV or os.name == "nt":
        logger.info(
            f"Running monothread version of server because we're using {'dev version' if _DEV else 'Windows'}"
        )
        import uvicorn

        server_args = {
            "workers": 1,
            "log_level": "debug",
            "reload": False,  # Makes class session_id volatile when reload=True
            "host": listen if listen else "0.0.0.0",
            "port": port if port else 9799,
        }
    else:
        import gunicorn.app.base

        class StandaloneApplication(gunicorn.app.base.BaseApplication):
            """
            This class supersedes gunicorn's class in order to load config before launching the app
            """

            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                config = {
                    key: value
                    for key, value in self.options.items()
                    if key in self.cfg.settings and value is not None
                }
                for key, value in config.items():
                    self.cfg.set(key.lower(), value)

            def load(self):
                return self.application

        server_args = {
            "workers": 4,  # Don't run multiple workers since we don't have shared variables yet (multiprocessing.cpu_count() * 2) + 1,
            "bind": f"{listen}:{port}" if listen else "0.0.0.0:9799",
            "worker_class": "uvicorn.workers.UvicornWorker",
        }

    try:
        if _DEV or os.name == "nt":
            uvicorn.run("grommunio_exporter.metrics:app", **server_args)
        else:
            StandaloneApplication(metrics.app, server_args).run()
    except KeyboardInterrupt as exc:
        logger.error("Program interrupted by keyoard: {}".format(exc))
        sys.exit(200)
    except Exception as exc:
        logger.error("Program interrupted by error: {}".format(exc))
        logger.critical("Trace:", exc_info=True)
        sys.exit(201)


def main():
    try:
        _main()
        worst_error = logger.get_worst_logger_level()
        if worst_error >= logging.WARNING:
            sys.exit(worst_error)
        sys.exit(0)
    except KeyboardInterrupt as exc:
        logger.error("Program interrupted by keyoard: {}".format(exc))
        sys.exit(200)
    except Exception as exc:
        logger.error("Program interrupted by error: {}".format(exc))
        logger.critical("Trace:", exc_info=True)
        sys.exit(201)


if __name__ == "__main__":
    main()
