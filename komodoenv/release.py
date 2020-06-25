from typing import Union
from pathlib import Path
from enum import Enum
from textwrap import dedent
import os
import subprocess
import json
import yaml


class PythonExecutableType(Enum):
    REAL = 0
    SHIM = 1


class Release:
    KOMODO_ROOT = Path("/prog/res/komodo")

    def __init__(self, path: Union[Path, str]):
        """Detect a komodo version of path"""
        if isinstance(path, Path):
            self._path = path.absolute()
        else:
            self._path = self.KOMODO_ROOT / path

        # Test that this is a valid komodo path
        self._realpath = self._path.resolve()
        self._release = self._realpath.name
        self._package_file = self._realpath / self._release
        self._packages = None
        assert self._package_file.exists()

        self._python_executable = self._path / "root" / "bin" / "python"
        assert self._python_executable.exists()

        # Get Python version and type
        self._version_info = self._get_sys("version_info")
        self._builtin_module_names = self._get_sys("builtin_module_names")

        # Heuristic to determine Komodo deploy type
        if (self._path / "root" / "libexec" / "python").exists():
            self._type = PythonExecutableType.SHIM
        else:
            self._type = PythonExecutableType.REAL

    @property
    def root(self):
        return self._path/"root"

    @property
    def packages(self):
        if self._packages is None:
            self._packages = yaml.safe_load(self._package_file.open())
        return self._packages

    @property
    def builtin_module_names(self):
        return self._builtin_module_names

    @property
    def version_info(self):
        return self._version_info

    @property
    def majver(self):
        return self._version_info[0]

    @property
    def minver(self):
        return self._version_info[1]

    @property
    def type(self):
        return self._type

    @property
    def libdir(self):
        return f"python{self.majver}.{self.minver}"

    def _get_sys(self, command):
        script = "import sys, json; print(json.dumps(tuple(sys.{})))".format(command)
        return json.loads(self.run(script))

    def run(self, script, env=None, args=None):
        if env is None:
            env = {}
        if args is None:
            args = []
        env["LD_LIBRARY_PATH"] = "{0}/lib:{0}/lib64".format(self.root)

        cmd = [self._python_executable, "-"] + list(args)
        print("Processo starto desu:", cmd)
        proc = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        if isinstance(script, str):
            script = bytes(script, "utf-8")

        stdout, stderr = proc.communicate(script)
        print(str(stdout, "utf-8"))
        proc.wait()
        return stdout
