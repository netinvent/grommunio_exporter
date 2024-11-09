#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of grommunio_exporter

__intname__ = "grommunio_exporter.filetime"
__author__ = "Orsiris de Jong"
__site__ = "https://www.github.com/netinvent/grommunio_exporter"
__description__ = "Grommunio Prometheus data exporter"


# This code has been balantly stolen from

import datetime


FILE_TIME_EPOCH = datetime.datetime(1601, 1, 1)
FILE_TIME_MICROSECOND = 10  # FILETIME counts 100 nanoseconds intervals = 0.1 microseconds, so 10 of those are 1 microsecond


def convert_from_file_time(file_time):
    microseconds_since_file_time_epoch = int(file_time) // FILE_TIME_MICROSECOND
    return FILE_TIME_EPOCH + datetime.timedelta(
        microseconds=microseconds_since_file_time_epoch
    )


def convert_to_file_time(date_time):
    microseconds_since_file_time_epoch = (
        date_time - FILE_TIME_EPOCH
    ) // datetime.timedelta(microseconds=1)
    return microseconds_since_file_time_epoch * FILE_TIME_MICROSECOND
