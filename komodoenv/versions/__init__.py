from .cpython27 import CPython27
from .cpython36 import CPython36


def get_creator_for_version(version_info):
    if version_info[:2] == [2, 7]:
        return CPython27
    if version_info[:2] == [3, 6]:
        return CPython36
    raise NotImplementedError
