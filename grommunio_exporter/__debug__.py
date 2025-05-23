#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of grommunio_exporter

__intname__ = "netinvent.__debug__"
__author__ = "Orsiris de Jong"
__site__ = "https://www.github.com/netinvent/grommunio_exporter"
__description__ = "Grommunio Prometheus data exporter"
__copyright__ = "Copyright (C) 2024-2025 NetInvent"
__license__ = "GPL-3.0-only"
__build__ = "2024110801"


import sys
import os
from typing import Callable
from functools import wraps
from logging import getLogger
import json


logger = getLogger()


# If set, debugging will be enabled by setting environment variable to __SPECIAL_DEBUG_STRING content
# Else, a simple true or false will suffice
__SPECIAL_DEBUG_STRING = ""
__debug_os_env = os.environ.get("_DEBUG", "False").strip("'\"")


if not __SPECIAL_DEBUG_STRING:
    if "--debug" in sys.argv:
        _DEBUG = True
        sys.argv.pop(sys.argv.index("--debug"))


if not "_DEBUG" in globals():
    _DEBUG = False
    if __SPECIAL_DEBUG_STRING:
        if __debug_os_env == __SPECIAL_DEBUG_STRING:
            _DEBUG = True
    elif __debug_os_env.capitalize() == "True":
        _DEBUG = True


def catch_exceptions(fn: Callable):
    """
    Catch any exception and log it so we don't loose exceptions in thread
    """

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            # pylint: disable=E1102 (not-callable)
            return fn(self, *args, **kwargs)
        except Exception as exc:
            # pylint: disable=E1101 (no-member)
            operation = fn.__name__
            logger.error(f"Function {operation} failed with: {exc}", level="error")
            logger.error("Trace:", exc_info=True)
            return None

    return wrapper


def fmt_json(js: dict):
    """
    Just a quick and dirty shorthand for pretty print which doesn't require pprint
    to be loaded
    """
    js = json.dumps(js, indent=4)
    return js
