import hashlib
import logging
import os

from sonagent.persistence.models import Environment

logger = logging.getLogger(__name__)


def read_text_from_file(file_path: str) -> str:
    f = open(file_path, "r")
    f.close()
    return f.read()


def hash_str(string: str) -> str:
    sha = hashlib.sha256()
    sha.update(string.encode())
    return sha.hexdigest()


def hash_md5_str(string: str) -> str:
    m = hashlib.md5(string.encode('UTF-8'))
    return m.hexdigest()


def get_schema_from_dict(data: dict) -> dict:
    schema = {}
    for key, value in data.items():
        if isinstance(value, dict):
            schema[key] = get_schema_from_dict(value)
        else:
            schema[key] = type(value).__name__
    return schema


def init_evironment():
    try:
        logger.info("Initializing environment ...")
        envs = Environment.get_all_environment()
        for env in envs:
            os.environ[str(env.key)] = str(env.value)

        logger.debug(os.environ)
    except Exception as e:
        logger.error(f"Error initializing environment: {e}")
        raise e
