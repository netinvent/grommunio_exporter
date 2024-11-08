#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of grommunio_exporter

__appname__ = "grommunio_exporter"
__author__ = "Orsiris de Jong"
__site__ = "https://www.github.com/netinvent/grommunio_exporter"
__description__ = "Grommunio Prometheus data exporter"
__copyright__ = "Copyright (C) 2024 NetInvent"
__license__ = "GPL-3.0-only"
__build__ = "2024110501"

from ofunctions.misc import fn_name
from logging import getLogger
from pathlib import Path
import time
import datetime
import json
from prometheus_client import Summary, Gauge, Enum
from command_runner import command_runner

# from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY

from grommunio_exporter.__debug__ import _DEBUG


logger = getLogger()


class GrommunioExporter:
    """
    Python class to discuss with grommunio CLI
    """

    def __init__(
        self,
        cli_binary: Path,
        hostname: str
    ):
        self.cli_binary = cli_binary
        self.hostname = hostname

        # Register gauges
        self.gauge_grommunio_mailbox_count = Gauge(
            "grommunio_mailbox_count",
            "Mailbox count",
            ["hostname", "domain"]
        )


        # Create a metric to track time spent and requests made.
        REQUEST_TIME = Summary(
            "request_processing_seconds", "Time spent processing request"
        )

    def get_mailboxes(self):
        """
        Uses grommunio-admin to fetch mailboxes
        """

        mailboxes = []

        cmd = f"{self.cli_binary} user query --format json-structured"
        exit_code, result = command_runner(cmd, timeout=60)
        if exit_code == 0:
            try:
                per_domain_count = {}
                mailboxes = json.loads(result)
                for mailbox in mailboxes:
                    try:
                        if "@" in mailbox["username"]:
                            user, domain = mailbox["username"].split('@')
                        else:
                            user = mailbox["username"]
                            domain = "No Domain"
                        try:
                            per_domain_count[domain].append(user)
                        except (KeyError, AttributeError):
                            per_domain_count[domain] = [user]
                    except (ValueError, TypeError, KeyError, IndexError) as exc:
                        logger.error(f"Cannot decode mailbox data: {exc}")
                        logger.debug("Trace:", exc_info=True)
                for domain, users in per_domain_count.items():
                    self.gauge_grommunio_mailbox_count.labels(self.hostname, domain).set(len(users))
            
            except json.JSONDecodeError as exc:
                logger.error(f"Cannot decode JSON: {exc}")
                logger.debug("Trace:", exc_info=True)
            except (TypeError, IndexError, AttributeError, KeyError) as exc:
                logger.error(f"Cannot interprete mailbox data: {exc}")
                logger.debug("Trace:", exc_info=True)
        else:
            logger.error(f"Could not execute {cmd}: Failed with error code {exit_code}: {result}")
            return mailboxes
        

    def get_mailbox_size(self, mailbox: str):
        """
        Get size of mailbox
        """
        cmd = f"{self.cli_binary} exmdb {mailbox} store get"
        exit_code, result = command_runner(cmd, timeout=60)
        if exit_code == 0:
            try:
                pass #WIP
            except:
                pass # WIP
    
if __name__ == "__main__":
    api = GrommunioExporter(cli_binary="/usr/sbin/grommunio-admin")
    api.get_mailboxes()