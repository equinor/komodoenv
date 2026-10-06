import json
import os
from collections.abc import Sequence
from pathlib import Path
from subprocess import PIPE, Popen


class Python:
    def __init__(
        self, executable: str | Path, komodo_prefix: str | Path | None = None
    ) -> None:
        """"""
        self.executable = Path(executable)

        if komodo_prefix is not None:
            self.komodo_prefix = komodo_prefix
        else:
            # Assume komodo's root is one directory up from executable
            self.komodo_prefix = self.executable.parent.parent

        self.root = self.executable.parent.parent
        self.version_info: tuple[int, int, int, str, int]
        self.site_paths: list[str]

    def make_dst(self, executable: str | Path) -> "Python":
        py = Python(executable, self.komodo_prefix)
        py.version_info = self.version_info
        return py

    def detect(self) -> None:
        """Detects what type of Python installation this is"""
        # Get python version_info
        script = b"import sys,json;print(json.dumps(sys.version_info[:]))"
        env = {
            "LD_LIBRARY_PATH": f"{self.komodo_prefix}/lib64:{self.komodo_prefix}/lib",
        }
        self.version_info = tuple(json.loads(self.call(script=script, env=env)))

        # Get python sys.path
        script = b"import sys,json;print(json.dumps(sys.path))"
        self.site_paths = json.loads(self.call(script=script, env=env))

    @property
    def version(self) -> str:
        return f"{self.version_info[0]}.{self.version_info[1]}"

    @property
    def site_packages_path(self) -> Path:
        return self.root / f"lib/python{self.version}/site-packages"

    def call(
        self,
        args: Sequence[str | Path] | None = None,
        env: dict[str, str] | None = None,
        script: bytes | None = None,
    ) -> bytes:
        if args is None:
            args = []
        if env is None:
            env = {}
        if script is not None:
            # Prepend '-' to tell Python to read from stdin
            args = ["-", *args]

        env["PATH"] = f"{self.executable.parent.absolute()}:{os.environ['PATH']}"
        env["LD_LIBRARY_PATH"] = f"{self.komodo_prefix}/lib64:{self.komodo_prefix}/lib"

        args = [self.executable, *args]
        proc = Popen([str(arg) for arg in args], stdin=PIPE, stdout=PIPE, env=env)
        stdout, _ = proc.communicate(script)

        return stdout
