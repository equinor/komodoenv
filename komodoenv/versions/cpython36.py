from .base_creator import BaseCreator
from komodoenv.actions import Create
from pathlib import Path


with open(str(Path(__file__).parent / "_site.py")) as f:
    _SITE_PY = Create("root/lib/python3.6/site.py", f.read())


class CPython36(BaseCreator):
    libdir           = "python3.6"
    required_modules = ("os","codecs","io","abc","_weakrefset","stat","posixpath","genericpath","_collections_abc")
    required_files   = ("lib-dynload","encodings")

    def get_extra_actions(self):
        return [_SITE_PY]
