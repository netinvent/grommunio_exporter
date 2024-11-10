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
import logging
from pathlib import Path
import json
from prometheus_client import Summary, Gauge, Enum
from command_runner import command_runner
from ofunctions.misc import BytesConverter
from grommunio_exporter.filetime import convert_from_file_time

# from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY

from grommunio_exporter.__debug__ import _DEBUG


logger = logging.getLogger()


class GrommunioExporter:
    """
    Python class to discuss with grommunio CLI
    """

    def __init__(self, cli_binary: Path, hostname: str):
        self.cli_binary = cli_binary
        self.hostname = hostname

        # API status variable
        self.api_status = True

        # Register gauges
        self.gauge_grommunio_api_status = Gauge(
            "grommunio_api_status", "Is API working ? 0 = ok, 1 = nok", ["hostname"]
        )

        self.gauge_grommunio_mailbox_count = Gauge(
            "grommunio_mailbox_count", "Mailbox count", ["hostname", "domain"]
        )

        self.gauge_grommunio_shared_mailbox_count = Gauge(
            "grommunio_shared_mailbox_count", "Mailbox count", ["hostname", "domain"]
        )

        self.gauge_grommunio_mailbox_messagesize = Gauge(
            "grommunio_mailbox_messagesize",
            "Mailbox current size",
            ["hostname", "domain", "username"],
        )

        self.gauge_grommunio_mailbox_storage_quota_limit = Gauge(
            "grommunio_mailbox_storage_quota_limit",
            "Mailbox storage quota limit",
            ["hostname", "domain", "username"],
        )

        self.gauge_grommunio_mailbox_prohibit_reveive_quota = Gauge(
            "grommunio_mailbox_prohibit_receive_limit",
            "Mailbox prohibit receive quota",
            ["hostname", "domain", "username"],
        )

        self.gauge_grommunio_mailbox_prohibit_send_quota = Gauge(
            "grommunio_mailbox_prohibit_send_quota",
            "Mailbox prohibit send quota",
            ["hostname", "domain", "username"],
        )

        self.gauge_grommunio_mailbox_creation_time = Gauge(
            "grommunio_mailbox_creation_time",
            "Mailbox creation time",
            ["hostname", "domain", "username"],
        )

        # Create a metric to track time spent and requests made.
        REQUEST_TIME = Summary(
            "request_processing_seconds", "Time spent processing request"
        )

    def _get_domain_from_username(self, username: str):
        if "@" in username:
            return username.split("@")[1]
        return "no_domain"

    def _get_mailboxes(self):
        """
        Used to fetch mailboxes

        grommunio-admin user query --format --json-structured

        Returns something like
        [{"ID":0,"username":"admin","status":0},{"ID":1,"username":"user@domain","status":0}]
        """

        mailboxes = []

        cmd = f"{self.cli_binary} user query --format json-structured"
        exit_code, result = command_runner(cmd, timeout=60)
        if exit_code == 0:
            try:
                per_domain_mailbox_count = {}
                per_domain_shared_mailbox_count = {}
                mailboxes = json.loads(result)
                for mailbox in mailboxes:
                    try:
                        username = mailbox["username"]
                        domain = self._get_domain_from_username(username)
                        # status = 4 is shared mailbox
                        if mailbox["status"] == 4:
                            try:
                                per_domain_shared_mailbox_count[domain].append(username)
                            except (KeyError, AttributeError):
                                per_domain_shared_mailbox_count[domain] = [username]
                        else:
                            try:
                                per_domain_mailbox_count[domain].append(username)
                            except (KeyError, AttributeError):
                                per_domain_mailbox_count[domain] = [username]
                    except (ValueError, TypeError, KeyError, IndexError) as exc:
                        logger.error(f"Cannot decode mailbox data: {exc}")
                        logger.debug("Trace:", exc_info=True)
                for domain, users in per_domain_mailbox_count.items():
                    self.gauge_grommunio_mailbox_count.labels(
                        self.hostname, domain
                    ).set(len(users))
                for domain, users in per_domain_shared_mailbox_count.items():
                    self.gauge_grommunio_shared_mailbox_count.labels(
                        self.hostname, domain
                    ).set(len(users))

            except json.JSONDecodeError as exc:
                logger.error(f"Cannot decode JSON: {exc}")
                logger.debug("Trace:", exc_info=True)
                self.api_status = False
            except (TypeError, IndexError, AttributeError, KeyError) as exc:
                logger.error(f"Cannot interprete mailbox data: {exc}")
                logger.debug("Trace:", exc_info=True)
                self.api_status = False
        else:
            logger.error(
                f"Could not execute {cmd}: Failed with error code {exit_code}: {result}"
            )
            self.api_status = False
        return mailboxes

    def get_mailboxes(self):
        """
        Just a wrapper to get exceptions from threads
        """
        try:
            return self._get_mailboxes()
        except Exception as exc:
            logger.error(f"Could not get mailboxes: {exc}")
            logger.debug("Trace", exc_info=True)
            self.api_status = False

    def _get_mailbox_properties(self, username: str):
        """
        Get size of mailbox

        grommunio-admin exmbd user@domain.tld store get
        will return something alike

        messagesizeextended                                                                                                                                          1923762702  1.79 GiB
        internetarticlenumber                                                                                                                                               158
        displayname                Some Guy                                                                                                                               15 B
        creationtime                                                                                                                                         133399827670000000  2023-09-24 00:46:07
        displaytypeex                                                                                                                                                         0
        storagequotalimit                                                                                                                                              18874368  18.0 GiB
        outofofficestate                                                                                                                                                      0
        0x66380102                 [90 bytes]
        prohibitreceivequota                                                                                                                                           16777216  16.0 GiB
        prohibitsendquota                                                                                                                                              15728640  15.0 GiB
        normalmessagesizeextended                                                                                                                                    1923662787  1.79 GiB
        assocmessagesizeextended                                                                                                                                          99915  97.6 kiB
        0x82c80102                 [6291 bytes]
        0x82c90102                 [1760 bytes]
        0x8346001f                 {"settings":{"zarafa":{"v1":{"main":{"thumbnail_photo":"data:image/jpeg;base64,/9j/4DFGDFGHDFGZJRgBAQEAVQBVsdfC/2wBDAAMDxxxxFMDAwMEAwMEBQgF…  4.97 kiB


        Only half of the grommunio-admin-api has --format json, so we need to come up with a little awk situation here
        We could also improve this by using regex, but let's be honest, it'll be easier for grommunio to implement --format here

        basically cmd is
        grommunio-admin exmdb user@domain.tld store get |awk ' BEGIN { printf"[" } {if ($1~/^0x/) {next} ; printf"\n%s{\"%s\": \"%s\"}", sep,$1,$2; sep=","} END { printf"]\n"}'
        """

        mailbox_properties = {}
        domain = self._get_domain_from_username(username)
        if domain == "no_domain":
            return mailbox_properties

        awk_cmd = r"""awk ' BEGIN { printf"[" } {if ($1~/^0x/) {next} ; printf"\n%s{\"%s\": \"%s\"}", sep,$1,$2; sep=","} END { printf"]\n"}'"""
        cmd = f"{self.cli_binary} exmdb {username} store get | {awk_cmd}"
        exit_code, result = command_runner(cmd, timeout=60, shell=True)
        if exit_code == 0:
            try:
                mbox_props_list = json.loads(result)
                for entry in mbox_props_list:
                    try:
                        # Get first key value pair (since we only have one)
                        mailbox_properties[list(entry.keys())[0]] = list(
                            entry.values()
                        )[0]
                    except (AttributeError, KeyError, TypeError, ValueError) as exc:
                        logger.errorf(
                            f"Cannot get mailbox properties from {entry}: {exc}"
                        )
            except json.JSONDecodeError as exc:
                logger.error(f"Cannot decode JSON: {exc}")
                logger.debug("Trace:", exc_info=True)
                self.api_status = False
        else:
            logger.error(
                f"Could not execute {cmd}: Failed with error code {exit_code}: {result}"
            )
            self.api_status = False
            # Since we used awk, we should definitly reset the output
            mailbox_properties = {}

        labels = (self.hostname, domain, username)
        for key, value in mailbox_properties.items():
            if key == "messagesizeextended":
                self.gauge_grommunio_mailbox_messagesize.labels(*labels).set(value)
            elif key == "storagequotalimit":
                # Value given in KB iec, we need to convert it to bytes
                value = BytesConverter(f"{value} KiB")
                self.gauge_grommunio_mailbox_storage_quota_limit.labels(*labels).set(
                    value
                )
            elif key == "prohibitreceivequota":
                value = BytesConverter(f"{value} KiB")
                self.gauge_grommunio_mailbox_prohibit_reveive_quota.labels(*labels).set(
                    value
                )
            elif key == "prohibitsendquota":
                value = BytesConverter(f"{value} KiB")
                self.gauge_grommunio_mailbox_prohibit_send_quota.labels(*labels).set(
                    value
                )
            elif key == "creationtime":
                # Creationtime is an 18-digit LDAP/FILETIME timestamp we need to convert first to epoch
                value = convert_from_file_time(value).timestamp()
                self.gauge_grommunio_mailbox_creation_time.labels(*labels).set(value)
        return mailbox_properties

    def get_mailbox_properties(self, username: str):
        """
        Just a wrapper to get exceptions from threads
        """
        try:
            return self._get_mailbox_properties(username)
        except Exception as exc:
            logger.error(f"Could not get mailboxes: {exc}")
            logger.debug("Trace", exc_info=True)
            self.api_status = False

    def api_status_reset(self):
        self.api_status = True

    def api_status_result(self):
        if self.api_status:
            self.gauge_grommunio_api_status.labels(self.hostname).set(0)
        else:
            self.gauge_grommunio_api_status.labels(self.hostname).set(0)


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    print("Running test API calls")
    api = GrommunioExporter(
        cli_binary="/usr/sbin/grommunio-admin", hostname="test-script"
    )
    mailboxes = api.get_mailboxes()
    print("Found mailboxes:")
    print(mailboxes)
    for mailbox in mailboxes:
        mailbox_properties = api.get_mailbox_properties(mailbox["username"])
        print("Mailbox properties:")
        print(mailbox_properties)
