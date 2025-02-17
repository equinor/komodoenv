from __future__ import annotations

import json
import os
from pathlib import Path
from subprocess import PIPE, Popen


class Python:
    def __init__(self, executable: Path) -> None:
        """"""
        self.executable = Path(executable)

        # Assume komodo's root is one directory up from executable
        # meaning, # root/bin/python
        self.release_root = self.executable.parents[1]

        self.version_info: tuple[str, str]
        self.site_paths: list[str]

    def make_dst(self, executable: Path) -> Python:
        py = Python(executable)
        py.version_info = self.version_info
        return py

    def detect(self) -> None:
        """Detects what type of Python installation this is"""
        # Get python version_info
        script = b"import sys,json;print(json.dumps(sys.version_info[0:2]))"
        self.version_info = tuple(json.loads(self.call(script=script)))

        # Get python sys.path
        script = b"import sys,json;print(json.dumps(sys.path))"
        self.site_paths = json.loads(self.call(script=script))

    @property
    def site_packages_path(self) -> Path:
        return (
            self.release_root
            / f"lib/python{self.version_info[0]}.{self.version_info[1]}/site-packages"
        )

    def call(self, script: bytes) -> bytes:
        env = {}
        env["PATH"] = f"{self.executable.parent.absolute()}:{os.environ['PATH']}"
        env["LD_LIBRARY_PATH"] = f"{self.release_root}/lib64:{self.release_root}/lib"

        # Prepend '-' to tell Python to read from stdin
        args = [str(self.executable), "-"]
        proc = Popen(args, stdin=PIPE, stdout=PIPE, env=env)
        stdout, _ = proc.communicate(script)

        return stdout
