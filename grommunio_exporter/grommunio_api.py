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
__build__ = "2025110701"

from typing import List
import logging
from pathlib import Path
import re
from prometheus_client import Summary, Gauge, Enum
import mysql.connector
from command_runner import command_runner
from ofunctions.misc import BytesConverter
from grommunio_exporter.filetime import convert_from_file_time
from grommunio_exporter.__version__ import __version__

# from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY

from grommunio_exporter.__debug__ import _DEBUG


logger = logging.getLogger()


class GrommunioExporter:
    """
    Python class to discuss with grommunio CLI
    """

    def __init__(
            self,
            mysql_config: dict,
            gromox_binary: Path,
            hostname: str):
        self.mysql_config = mysql_config
        self.gromox_binary = gromox_binary
        self.hostname = hostname

        self.mysql_cnx = mysql.connector.connect(
            **mysql_config
        )

        self.mysql_cursor = self.mysql_cnx.cursor(dictionary=True)

        # API status variable
        self.api_status = True

        # Register gauges
        self.gauge_grommunio_exporter_version = Gauge(
            "grommunio_exporter_version",
            "Grommunio Exporter version",
            ["hostname", "version"],
        )

        self.gauge_grommunio_gromox_version = Gauge(
            "grommunio_gromox_version",
            "Grommunio Gromox version",
            ["hostname", "version"],
        )

        self.gauge_grommunio_admin_version = Gauge(
            "grommunio_admin_version",
            "Grommunio Admin version",
            ["hostname", "version"],
        )

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

        self.gauge_grommunio_mailbox_out_of_office_state = Gauge(
            "grommunio_mailbox_out_of_office_state",
            "Mailbox out of office state",
            ["hostname", "domain", "username"],
        )

        # Create a metric to track time spent and requests made.
        REQUEST_TIME = Summary(
            "request_processing_seconds", "Time spent processing request"
        )

    def get_grommunio_versions(self):
        versions = {
            "grommunio_exporter": __version__,
            "gromox": "unknown",
        }

        cmd = f"{self.gromox_binary} --version"
        exit_code, result = command_runner(cmd, timeout=10)
        if exit_code == 0:
            version = re.search(r"gromox-zcore\s(.*)\s\(pid.*", result)
            if version:
                version = version.group(1)
                versions["gromox"] = version.strip()
        return versions

    def update_grommunio_versions_gauges(self, version: dict):
        self.gauge_grommunio_exporter_version.labels(
            self.hostname, version["grommunio_exporter"]
        ).set(0)
        self.gauge_grommunio_gromox_version.labels(
            self.hostname, version["gromox"]
        ).set(0 if version["gromox"] != "unknown" else 1)

    def _get_domain_from_username(self, username: str):
        if "@" in username:
            return username.split("@")[1]
        return "no_domain"

    def _get_mailboxes(self, filter_mailing_lists: bool = True):
        """
        Used to fetch mailboxes

        grommunio-admin user query --format --json-structured

        Returns something like
        [{"ID":0,"username":"admin","status":0},{"ID":1,"username":"user@domain","status":0}]

        The following query returns something like:
        [{'id': 0, 'username': 'admin', 'address_status': 0}, {'id': 1, 'username': 'user@domain.tld', 'address_status': 0}
        """

        mailboxes = {}

        query = "SELECT id, username, address_status FROM users"
        if filter_mailing_lists:
            query += " WHERE username NOT IN (SELECT listname FROM mlists);"
        query += ";"

        self.mysql_cursor.execute(query)
        mailboxes = self.mysql_cursor.fetchall()
        return mailboxes

    def update_mailbox_gauges(self, mailboxes: dict):
        try:
            per_domain_mailbox_count = {}
            per_domain_shared_mailbox_count = {}
            for mailbox in mailboxes:
                try:
                    username = mailbox["username"]
                    domain = self._get_domain_from_username(username)
                    # address_status = 4 is shared mailbox
                    if mailbox["address_status"] == 4:
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
                self.gauge_grommunio_mailbox_count.labels(self.hostname, domain).set(
                    len(users)
                )
            for domain, users in per_domain_shared_mailbox_count.items():
                self.gauge_grommunio_shared_mailbox_count.labels(
                    self.hostname, domain
                ).set(len(users))
        except (TypeError, AttributeError, KeyError, IndexError, ValueError) as exc:
            logger.error(f"Cannot iter over mailboxes while updating gauges: {exc}")
            logger.debug("Trace:", exc_info=True)
            self.api_status = False

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

    def get_usernames_from_mailboxes(
        self, mailboxes: list, filter_no_domain: bool = True
    ) -> List[str]:
        """
        Extract a list of usernames from mailboxes
        """
        usernames = []
        for mailbox in mailboxes:
            if filter_no_domain:
                domain = self._get_domain_from_username(mailbox["username"])
                if domain == "no_domain":
                    continue
            usernames.append(mailbox["username"])
        return usernames

    def _get_mailbox_properties(self, usernames: List[str]):
        """
        In Grommunio database:

        Hex         Proptag         Name                      Type
        0x666a0003  1718222851     PROHIBITRECEIVEQUOTA       LONG
        0x0e080014  235405332      MESSAGESIZEEXTENDED        LONGLONG
        0x0e230003  237174787      INTERNETARTICLENUMBER      LONG
        0x3001001f  805371935      DISPLAYNAME                WSTRING
        0x39050003  956628995      DISPLAYTYPEEX              LONG
        0x3ff50003  1073020931     STORAGEQUOTALIMIT          LONG
        0x661d000b  1713176587     OUTOFOFFICESTATE           BYTE
        0x666a0003  1718222851     PROHIBITRECEIVEQUOTA       LONG
        0x666e0003  1718484995     PROHIBITSENDQUOTA          LONG
        0x66b30014  1723006996     NORMALMESSAGESIZEEXTENDED  LONGLONG
        0x66b40014  1723072532     ASSOCMESSAGESIZEEXTENDED   LONGLONG
        0x30070040  805765184      CREATIONTIME               FILETIME

        
        # Raw request
        SELECT
            users.id,
            users.username,
            user_properties.proptag,
            user_properties.propval_str 
        FROM user_properties INNER JOIN users ON user_properties.user_id=users.id 
        WHERE user_properties.proptag IN (1718222851,235405332,1073020931,1718484995, 805765184);

        # Let's transform the proptag values into a column
        SELECT
            users.id,
            users.username,
            MAX(CASE WHEN user_properties.proptag = 235405332 THEN user_properties.propval_str END) AS messagesizeextended,
            MAX(CASE WHEN user_properties.proptag = 1718222851 THEN user_properties.propval_str END) AS prohibitreceivequota,
            MAX(CASE WHEN user_properties.proptag = 1073020931 THEN user_properties.propval_str END) AS storagequotalimit,
            MAX(CASE WHEN user_properties.proptag = 1718484995 THEN user_properties.propval_str END) AS prohibitsendquota,
            MAX(CASE WHEN user_properties.proptag = 805765184 THEN user_properties.propval_str END) AS creationtime,
            MAX(CASE WHEN user_properties.proptag = 1713176587 THEN user_properties.propval_str END) AS outofofficestate
        FROM user_properties INNER JOIN users ON user_properties.user_id=users.id
        WHERE user_properties.proptag IN (1718222851,235405332,1073020931,1718484995,805765184,1713176587)
        GROUP BY users.id;

        Produces something like:
        [
        {'id': 1, 'username': 'user@domain.tld', 'messagesizeextended': '5025442101', 'prohibitreceivequota': None, 'storagequotalimit': '25165824', 'prohibitsendquota': None, 'creationtime': '133399826720000000'},
        {'id': 2, 'username': 'other@user.tld', 'messagesizeextended': '2778305272', 'prohibitreceivequota': '16777216', 'storagequotalimit': '18874368', 'prohibitsendquota': '15728640', 'creationtime': '133399827670000000'}
        ]
        """

        mailbox_properties = {}

        query = "SELECT \
            users.id, \
            users.username, \
            MAX(CASE WHEN user_properties.proptag = 235405332 THEN user_properties.propval_str END) AS messagesizeextended, \
            MAX(CASE WHEN user_properties.proptag = 1718222851 THEN user_properties.propval_str END) AS prohibitreceivequota, \
            MAX(CASE WHEN user_properties.proptag = 1073020931 THEN user_properties.propval_str END) AS storagequotalimit, \
            MAX(CASE WHEN user_properties.proptag = 1718484995 THEN user_properties.propval_str END) AS prohibitsendquota, \
            MAX(CASE WHEN user_properties.proptag = 805765184 THEN user_properties.propval_str END) AS creationtime, \
            MAX(CASE WHEN user_properties.proptag = 1713176587 THEN user_properties.propval_str END) AS outofofficestate \
        FROM user_properties INNER JOIN users ON user_properties.user_id=users.id \
        WHERE user_properties.proptag IN (1718222851,235405332,1073020931,1718484995,805765184,1713176587) \
        GROUP BY users.id;"
        self.mysql_cursor.execute(query)
        mailbox_properties = self.mysql_cursor.fetchall()
        return mailbox_properties

    def update_mailbox_properties_gauges(self, mailbox_properties: dict):
        try:
            for mbox_prop in mailbox_properties:
                username = "none"
                labels = (self.hostname, "no_domain", "none")
                for key, value in mbox_prop.items():
                    if value is None:
                        value = 0
                    if key == "username":
                        username = value
                        domain = self._get_domain_from_username(username)
                        labels = (self.hostname, domain, username)
                    if key == "messagesizeextended":
                        self.gauge_grommunio_mailbox_messagesize.labels(
                            *labels
                        ).set(value)
                    elif key == "storagequotalimit":
                        # Value given in KB iec, we need to convert it to bytes
                        value = BytesConverter(f"{value} KiB")
                        self.gauge_grommunio_mailbox_storage_quota_limit.labels(
                            *labels
                        ).set(value)
                    elif key == "prohibitreceivequota":
                        value = BytesConverter(f"{value} KiB")
                        self.gauge_grommunio_mailbox_prohibit_reveive_quota.labels(
                            *labels
                        ).set(value)
                    elif key == "prohibitsendquota":
                        value = BytesConverter(f"{value} KiB")
                        self.gauge_grommunio_mailbox_prohibit_send_quota.labels(
                            *labels
                        ).set(value)
                    elif key == "creationtime":
                        # Creationtime is an 18-digit LDAP/FILETIME timestamp we need to convert first to epoch
                        value = convert_from_file_time(value).timestamp()
                        self.gauge_grommunio_mailbox_creation_time.labels(
                            *labels
                        ).set(value)
                    elif key == "outofofficestate":
                        self.gauge_grommunio_mailbox_out_of_office_state.labels(
                            *labels
                        ).set(value)
        except (TypeError, AttributeError, KeyError, IndexError, ValueError) as exc:
            logger.error(
                f"Cannot iter over mailbox properties while updating gauges: {exc}"
            )
            logger.debug("Trace:", exc_info=True)
            self.api_status = False

    def get_mailbox_properties(self, usernames: List[str]):
        try:
            return self._get_mailbox_properties(usernames)
        except Exception as exc:
            logger.error(f"Could not get mailboxes properties: {exc}")
            logger.debug("Trace", exc_info=True)
            self.api_status = False

    def api_status_reset(self):
        self.api_status = True

    def update_api_gauges(self):
        if self.api_status:
            self.gauge_grommunio_api_status.labels(self.hostname).set(0)
        else:
            self.gauge_grommunio_api_status.labels(self.hostname).set(1)


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    print("Running test API calls")
    from grommunio_exporter.mysql_config import load_mysql_config
    mysql_config = load_mysql_config()
    api = GrommunioExporter(
        mysql_config=mysql_config,
        gromox_binary="/usr/libexec/gromox/zcore",
        hostname="test-script",
    )

    print("Getting Grommunio versions")
    versions = api.get_grommunio_versions()
    print(versions)
    mailboxes = api.get_mailboxes()
    print("Found mailboxes:")
    print(mailboxes)
    usernames = api.get_usernames_from_mailboxes(mailboxes)
    print("Found usernames:")
    print(usernames)
    mailbox_properties = api.get_mailbox_properties(usernames)
    print("Mailbox properties:")
    print(mailbox_properties)

    print("Updating gauges for Grommunio versions")
    api.update_grommunio_versions_gauges(versions)
    print("Updating gauges for mailboxes")
    api.update_mailbox_gauges(mailboxes)
    print("Updating gauges for mailbox properties")
    api.update_mailbox_properties_gauges(mailbox_properties)
    print("Updating gauges for API status")
    api.update_api_gauges()
