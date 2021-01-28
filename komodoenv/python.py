import os
import json

from typing import Any, List, Optional, Tuple
from subprocess import Popen, PIPE
from pathlib import Path
from enum import Enum


class PythonType(Enum):
    UNKNOWN = 0
    REAL = 1
    SHIM = 2
    VENV = 3


class Python:
    def __init__(self, executable: Path, komodo_prefix: Path = None) -> None:
        """"""
        self.executable = Path(executable)

        if komodo_prefix is not None:
            self.komodo_prefix = komodo_prefix
        else:
            # Assume komodo's root is one directory up from executable
            self.komodo_prefix = self.executable.parent.parent

        self.root = self.executable.parent.parent
        self.type = PythonType.UNKNOWN
        self.version_info: Tuple[Any, ...] = (0, 0, 0)

    def make_dst(self, executable: Path) -> "Python":
        py = Python(executable, self.komodo_prefix)
        py.type = self.type
        py.version_info = self.version_info
        return py

    def detect(self) -> None:
        """Detects what type of Python installation this is"""
        # Get python version_info
        script = b"import sys,json;print(json.dumps(sys.version_info[:]))"
        env = {"LD_LIBRARY_PATH": "{0}/lib64:{0}/lib".format(self.komodo_prefix)}
        self.version_info = tuple(json.loads(self.call(script=script, env=env)))

        # Get python sys.path
        script = b"import sys,json;print(json.dumps(sys.path))"
        self.site_paths = json.loads(self.call(script=script, env=env))

        # Existence of libexec suggests that this is a libexec-shim komodo release
        libexec_python = self.root / "libexec" / "python"
        if libexec_python.exists():
            self.type = PythonType.SHIM
            return

        # Virtualenv adds a sys.real_prefix constant to the sys module. We can
        # use this to check whether this is a real Python install or a
        # virtualenv.
        script = b"import sys;print(hasattr(sys,'real_prefix'))"
        if self.call(script=script, env=env) == "True":
            self.type = PythonType.VENV
        else:
            self.type = PythonType.REAL

    def is_shim(self) -> bool:
        return self.type == PythonType.SHIM

    @property
    def site_packages_path(self) -> Path:
        return self.root / "lib/python{}.{}/site-packages".format(*self.version_info)

    def call(
        self,
        args: Optional[List[str]] = None,
        env: Optional[dict] = None,
        script: Optional[bytes] = None,
    ) -> bytes:
        if args is None:
            args = []
        if env is None:
            env = {}
        if script is not None:
            # Prepend '-' to tell Python to read from stdin
            args = ["-"] + args

        env["PATH"] = "{}:{}".format(
            self.executable.parent.absolute(), os.environ["PATH"]
        )
        env["LD_LIBRARY_PATH"] = "{0}/lib64:{0}/lib".format(self.komodo_prefix)

        args = [str(self.executable)] + [str(x) for x in args]
        proc = Popen(args, stdin=PIPE, stdout=PIPE, env=env)
        stdout, _ = proc.communicate(script)

        return stdout
