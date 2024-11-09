#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of grommunio_exporter

__intname__ = "grommunio_exporter.__version__"
__author__ = "Orsiris de Jong"
__site__ = "https://www.github.com/netinvent/grommunio_exporter"
__description__ = "Grommunio Prometheus data exporter"
__copyright__ = "Copyright (C) 2024 NetInvent"
__license__ = "GPL-3.0-only"
__build__ = "2024110801"


from typing import Optional, List, Any, Union
from pathlib import Path
from logging import getLogger
from cryptidy import symmetric_encryption as enc
from ruamel.yaml import YAML
from ruamel.yaml.compat import ordereddict
from ruamel.yaml.comments import CommentedMap
from ofunctions.misc import replace_in_iterable

ID_STRING = "__GROMMUNIO_EXPORTER__"
ENCRYPTED_OPTIONS = ["username", "password"]
AES_KEY = b"p\xfei\n\xfe\xad\xb8\x06;\xae\x0e\x14[\xa5\x97\xb0\xaf\xa9\xefHV\x88qKe\x8cP\xd9\xcd \xe5b"


default_config_dict = {
    "http_server": {
        "port": 9799,
        "listen": "0.0.0.0",
        "log_file": "/var/log/grommunio_exporter.log",
        "no_auth": True,
        "username": None,
        "password": None,
    }
}

logger = getLogger()


# Monkeypatching ruamel.yaml ordreddict so we get to use pseudo dot notations
# eg data.g('my.array.keys') == data['my']['array']['keys']
# and data.s('my.array.keys', 'new_value')
def g(self, path, sep=".", default=None, list_ok=False):
    """
    Getter for dot notation in an a dict/OrderedDict
    print(d.g('my.array.keys'))
    """
    try:
        return self.mlget(path.split(sep), default=default, list_ok=list_ok)
    except AssertionError as exc:
        logger.debug(
            f"CONFIG ERROR {exc} for path={path},sep={sep},default={default},list_ok={list_ok}"
        )
        raise AssertionError


ordereddict.g = g


def convert_to_commented_map(
    source_dict,
):
    if isinstance(source_dict, dict):
        return CommentedMap(
            {k: convert_to_commented_map(v) for k, v in source_dict.items()}
        )
    else:
        return source_dict


def key_should_be_encrypted(key: str, encrypted_options: List[str]):
    """
    Checks whether key should be encrypted
    """
    if key:
        for option in encrypted_options:
            if option in key:
                return True
    return False


def crypt_config(
    full_config: dict, aes_key: str, encrypted_options: List[str], operation: str
):
    try:

        def _crypt_config(key: str, value: Any) -> Any:
            if key_should_be_encrypted(key, encrypted_options):
                if value is not None:
                    if operation == "encrypt":
                        if (
                            isinstance(value, str)
                            and (
                                not value.startswith(ID_STRING)
                                or not value.endswith(ID_STRING)
                            )
                        ) or not isinstance(value, str):
                            value = enc.encrypt_message_hf(
                                value, aes_key, ID_STRING, ID_STRING
                            ).decode("utf-8")
                    elif operation == "decrypt":
                        if (
                            isinstance(value, str)
                            and value.startswith(ID_STRING)
                            and value.endswith(ID_STRING)
                        ):
                            _, value = enc.decrypt_message_hf(
                                value,
                                aes_key,
                                ID_STRING,
                                ID_STRING,
                            )
                    else:
                        raise ValueError(f"Bogus operation {operation} given")
            return value

        return replace_in_iterable(
            full_config,
            _crypt_config,
            callable_wants_key=True,
            callable_wants_root_key=True,
        )
    except Exception as exc:
        logger.error(f"Cannot {operation} configuration: {exc}.")
        logger.debug("Trace:", exc_info=True)
        return False


def is_encrypted(full_config: dict) -> bool:
    is_encrypted = True

    def _is_encrypted(key, value) -> Any:
        nonlocal is_encrypted

        if key_should_be_encrypted(key, ENCRYPTED_OPTIONS):
            if value is not None:
                if isinstance(value, str) and (
                    not value.startswith(ID_STRING) or not value.endswith(ID_STRING)
                ):
                    is_encrypted = False
        return value

    replace_in_iterable(
        full_config,
        _is_encrypted,
        callable_wants_key=True,
        callable_wants_root_key=True,
    )
    return is_encrypted


def _load_config_file(config_file: Path) -> Union[bool, dict]:
    """
    Checks whether config file is valid
    """
    try:
        with open(config_file, "r", encoding="utf-8") as file_handle:
            yaml = YAML(typ="rt")
            full_config = yaml.load(file_handle)
            if not full_config:
                logger.critical("Config file seems empty !")
                return False
            return full_config
    except OSError:
        logger.critical(f"Cannot load configuration file from {config_file}")
        return False


def load_config(config_file: Path) -> Optional[dict]:
    logger.info(f"Loading configuration file {config_file}")

    full_config = _load_config_file(config_file)
    if not full_config:
        return None
    config_file_is_updated = False

    # Check if we need to encrypt some variables
    if not is_encrypted(full_config):
        logger.info("Encrypting non encrypted data in configuration file")
        config_file_is_updated = True
    # Decrypt variables
    full_config = crypt_config(
        full_config, AES_KEY, ENCRYPTED_OPTIONS, operation="decrypt"
    )
    if not full_config:
        msg = "Cannot decrypt config file"
        logger.critical(msg)
        raise EnvironmentError(msg)

    # save config file if needed
    if config_file_is_updated:
        logger.info("Updating config file")
        save_config(config_file, full_config)
    return convert_to_commented_map(full_config)


def save_config(config_file: Path, full_config: dict) -> bool:
    try:
        with open(config_file, "w", encoding="utf-8") as file_handle:
            if not is_encrypted(full_config):
                full_config = crypt_config(
                    full_config, AES_KEY, ENCRYPTED_OPTIONS, operation="encrypt"
                )
            yaml = YAML(typ="rt")
            yaml.dump(full_config, file_handle)
        # Since yaml is a "pointer object", we need to decrypt after saving
        full_config = crypt_config(
            full_config, AES_KEY, ENCRYPTED_OPTIONS, operation="decrypt"
        )
        return True
    except OSError:
        logger.critical(f"Cannot save configuration file to {config_file}")
        return False


def get_default_config():
    return convert_to_commented_map(default_config_dict)
