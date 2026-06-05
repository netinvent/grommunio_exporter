#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of grommunio_exporter

__intname__ = "grommunio_exporter.mysql_config"
__author__ = "Orsiris de Jong"
__site__ = "https://www.github.com/netinvent/grommunio_exporter"
__description__ = "Grommunio Prometheus data exporter"


from logging import getLogger
import configparser

logger = getLogger()


def load_mysql_config() -> dict:
    config = configparser.ConfigParser()
    try:
        with open("/etc/gromox/mysql_adaptor.cfg") as stream:
            config.read_string("[top]\n" + stream.read())
            return {
                "user": config["top"]["mysql_username"],
                "password": config["top"]["mysql_password"],
                "database": config["top"]["mysql_dbname"],
                "host": "localhost",
                "port": 3306,
            }
    except OSError:
        logger.error("Cannot read /etc/gromox/mysql_adaptor.cfg file")
    return {
        "user": None,
        "password": None,
        "database": None,
        "host": "localhost",
        "port": 3306,
    }
