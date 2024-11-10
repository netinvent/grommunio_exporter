#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#e
# This file is part of grommunio_exporter

__appname__ = "grommunio_exporter"
__author__ = "Orsiris de Jong"
__site__ = "https://www.github.com/netinvent/grommunio_exporter"
__description__ = "Grommunio Prometheus data exporter"
__copyright__ = "Copyright (C) 2024 NetInvent"
__license__ = "GPL-3.0-only"
__build__ = "2024110501"
__setup_ver__ = "1.0.0"


PACKAGE_NAME = "grommunio_exporter"
DESCRIPTION = "Grommunio email system data exporter for Prometheus"

import sys
import os
import pkg_resources
import setuptools


def _read_file(filename):
    here = os.path.abspath(os.path.dirname(__file__))
    if sys.version_info[0] < 3:
        # With python 2.7, open has no encoding parameter, resulting in TypeError
        # Fix with io.open (slow but works)
        from io import open as io_open

        try:
            with io_open(
                os.path.join(here, filename), "r", encoding="utf-8"
            ) as file_handle:
                return file_handle.read()
        except IOError:
            # Ugly fix for missing requirements.txt file when installing via pip under Python 2
            return ""
    else:
        with open(os.path.join(here, filename), "r", encoding="utf-8") as file_handle:
            return file_handle.read()


def get_metadata(package_file):
    """
    Read metadata from package file
    """

    _metadata = {}

    for line in _read_file(package_file).splitlines():
        if line.startswith("__version__") or line.startswith("__description__"):
            delim = "="
            _metadata[line.split(delim)[0].strip().strip("__")] = (
                line.split(delim)[1].strip().strip("'\"")
            )
    return _metadata


def parse_requirements(filename):
    """
    There is a parse_requirements function in pip but it keeps changing import path
    Let's build a simple one
    """
    try:
        requirements_txt = _read_file(filename)
        install_requires = [
            str(requirement)
            for requirement in pkg_resources.parse_requirements(requirements_txt)
        ]
        print(install_requires)
        return install_requires
    except OSError:
        print(
            'WARNING: No requirements.txt file found as "{}". Please check path or create an empty one'.format(
                filename
            )
        )


# With this, we can enforce a binary package.
class BinaryDistribution(setuptools.Distribution):
    """Distribution which always forces a binary package with platform name"""

    @staticmethod
    def has_ext_modules():
        return True


package_path = os.path.abspath(PACKAGE_NAME)
for path in ["__main__.py", PACKAGE_NAME + ".py"]:
    package_file = os.path.join(package_path, "__version__.py")
    if os.path.isfile(package_file):
        break
metadata = get_metadata(package_file)
requirements = parse_requirements(
    os.path.join(package_path, os.pardir, "requirements.txt")
)
long_description = _read_file("README.md")


console_scripts = [
    "grommunio_exporter = grommunio_exporter.server:main"
]
setuptools.setup(
    name=PACKAGE_NAME,
    # We may use find_packages in order to not specify each package manually
    # packages = ['command_runner'],
    packages=setuptools.find_packages(),
    version=metadata["version"],
    install_requires=requirements,
    classifiers=[
        # command_runner is mature
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: System",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    description=DESCRIPTION,
    license="GPLv3",
    author="NetInvent - Orsiris de Jong",
    author_email="contact@netinvent.fr",
    url="https://github.com/netinvent/grommunio_exporter",
    keywords=[
        "mail",
        "grommunio",
        "prometheus",
        "linux",
        "cli",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    entry_points={
        "console_scripts": console_scripts,
    },
    # As we do version specific hacks for installed inline copies, make the
    # wheel version and platform specific.
    # distclass=BinaryDistribution,
)
