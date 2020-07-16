from .base_creator import BaseCreator
from komodoenv.actions import Create
from pathlib import Path


with open(str(Path(__file__).parent / "_site.py")) as f:
    _SITE_PY = Create("root/lib/python2.7/site.py", f.read())


class CPython27(BaseCreator):
    libdir           = "python2.7"
    required_modules = ("os",)
    required_files   = ("lib-dynload",)

    def get_extra_actions(self):
        return [_SITE_PY]
