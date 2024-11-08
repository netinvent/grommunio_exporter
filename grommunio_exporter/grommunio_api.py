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
import time
import datetime
import json
from prometheus_client import Summary, Gauge, Enum
from command_runner import command_runner

# from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY

from grommunio_exporter.__debug__ import _DEBUG


logger = getLogger(_DEBUG)


class GrommunioExporter:
    """
    Python bindings for Altaro API
    """

    def __init__(
        self,
        cli_binary
    ):
        self.cli_binary = cli_binary

        # Register gauges
        self.gauge_grommunio_mailbox_count = Gauge(
            "grommunio_mailbox_count",
            "Mailbox count",
            ["domain"]
        )

        self.gauge_altaro_api_success = Gauge(
            "altaro_api_success",
            "Altaro API request success 0 = success, 1 = cannot connect, 2 = api error",
        )

        self.gauge_lastbackup = Gauge(
            "altaro_lastbackup_timestamp",
            "Timestamp of last backup",
            ["vmname", "hostname", "vmuuid"],
        )
        self.gauge_lastoffsitecopy = Gauge(
            "altaro_lastoffsitecopy_timestamp",
            "Timestamp of last offsite copy",
            ["vmname", "hostname", "vmuuid"],
        )

        self.gauge_lastbackup_duration = Gauge(
            "altaro_lastbackup_duration_seconds",
            "Duration of last backup",
            ["vmname", "hostname", "vmuuid"],
        )
        self.gauge_lastoffsitecopy_duration = Gauge(
            "altaro_lastoffsitecopy_duration_seconds",
            "Duration of last offsite copy",
            ["vmname", "hostname", "vmuuid"],
        )

        self.gauge_lastbackup_transfersize_compressed = Gauge(
            "altaro_lastbackup_transfersize_compressed_bytes",
            "Compressed size of last backup",
            ["vmname", "hostname", "vmuuid"],
        )
        self.gauge_lastbackup_transfersize_uncompressed = Gauge(
            "altaro_lastbackup_transfersize_uncompressed_bytes",
            "Unompressed size of last backup",
            ["vmname", "hostname", "vmuuid"],
        )

        self.gauge_lastoffsitecopy_transfersize_compressed = Gauge(
            "altaro_lastoffsitecopy_transfersize_compressed_bytes",
            "Compressed size of last offsite copy",
            ["vmname", "hostname", "vmuuid"],
        )
        self.gauge_lastoffsitecopy_transfersize_uncompressed = Gauge(
            "altaro_lastoffsitecopy_transfersize_uncompressed_bytes",
            "Uncompressed size of last offsite copy",
            ["vmname", "hostname", "vmuuid"],
        )
        self.gauge_lastbackup_result = Gauge(
            "altaro_lastbackup_result",
            "Result of last backup 0 = success, 1 = warning, 2 = error, 3 = unknown, 4 = other",
            ["vmname", "hostname", "vmuuid"],
        )

        self.gauge_lastoffsitecopy_result = Gauge(
            "altaro_lastoffsitecopy_result",
            "Result of last offsite copy 0 = success, 1 = warning, 2 = error, 3 = unknown, 4 = other",
            ["vmname", "hostname", "vmuuid"],
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

        cmd = f"{self.cli_binary} user query --format json"
        exit_code, result = command_runner(cmd, timeout=60)
        if exit_code == 0:
            try:
                per_domain_count = {}
                mailboxes = json.loads(result)
                for mailbox in mailboxes:
                    try:
                        user, domain = mailbox["username"].split('@')
                        try:
                            per_domain_count[domain].append(user)
                        except AttributeError:
                            per_domain_count[domain] = [user]
                    except (ValueError, TypeError, KeyError, IndexError) as exc:
                        logger.error(f"Cannot decode mailbox data: {exc}")
                        logger.debug("Trace:", exc_info=True)
                for domain, users in per_domain_count.items():
                    self.gauge_grommunio_mailbox_count.labels(domain).set(len(users))
            
            except json.JSONDecodeError as exc:
                logger.error(f"Cannot decode JSON: {exc}")
                logger.debug("Trace:", exc_info=True)
            except (TypeError, IndexError, AttributeError, KeyError) as exc:
                logger.error(f"Cannot interprete mailbox data: {exc}")
                logger.debug("Trace:", exc_info=True)
            
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
    