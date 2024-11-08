#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of altaro_exporter

__appname__ = "grommunio_exporter"
__author__ = "Orsiris de Jong"
__site__ = "https://www.github.com/netinvent/grommunio_exporter"
__description__ = "Grommunio Prometheus data exporter"
__copyright__ = "Copyright (C) 2024 NetInvent"
__license__ = "GPL-3.0-only"
__build__ = "2024110501"


import sys
from logging import getLogger
import secrets
from argparse import ArgumentParser
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi_offline import FastAPIOffline
from grommunio_exporter.__version__ import __version__
from grommunio_exporter.configuration import load_config
from grommunio_exporter.grommunio_api import GrommunioExporter
import prometheus_client


logger = getLogger()


# Make sure we load given config files again
default_config_file = "grommunio_exporter.yaml"
parser = ArgumentParser()
parser.add_argument(
    "-c",
    "--config-file",
    dest="config_file",
    type=str,
    default=default_config_file,
    required=False,
    help="Path to grommunio_exporter.yaml file",
)
args = parser.parse_args()
if args.config_file:
    config_dict = load_config(args.config_file)
else:
    logger.critical("No configuration file given. Exiting.")
    sys.exit(1)

if not config_dict:
    logger.critical("No configuration file loaded. Exiting.")
    sys.exit(1)

http_username = config_dict.http_server.username
http_password = config_dict.http_server.password
http_no_auth = config_dict.http_server.no_auth
cli_binary = config_dict.grommunio_admin_binary
if not cli_binary:
    cli_binary = "/usr/sbin/grommunio-admin"

app = FastAPIOffline()
metrics_app = prometheus_client.make_asgi_app()
app.mount("/metrics", metrics_app)
security = HTTPBasic()

api = GrommunioExporter(cli_binary=cli_binary)



def anonymous_auth():
    return "anonymous"


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = http_username.encode("utf-8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = http_password.encode("utf-8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


try:
    if http_no_auth is True:
        logger.warning("Running without HTTP authentication")
        auth_scheme = anonymous_auth
    else:
        logger.info("Running with HTTP authentication")
        auth_scheme = get_current_username
except (KeyError, AttributeError, TypeError):
    auth_scheme = get_current_username
    logger.info("Running with HTTP authentication")


@app.get("/")
async def api_root(auth=Depends(auth_scheme)):
    return {"app": __appname__, "version": __version__}


@app.get("/metrics")
async def get_metrics(auth=Depends(auth_scheme)):
    try:
        api.get_mailboxes()
        #api.get_mailbox_sizes()
    except KeyError:
        logger.critical("Bogus configuration file. Missing Altaro_hosts key.")
    return Response(
        content=prometheus_client.generate_latest(), media_type="text/plain"
    )
