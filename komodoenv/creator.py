from pathlib import Path
import subprocess
import shutil
import re
import os
import sys
import logging
import distro
from typing import Any, IO, Optional, Union
from textwrap import dedent
from tempfile import mkdtemp
from colors import green, strip_color
from pkg_resources import get_distribution

from komodoenv.python import Python
from komodoenv.bundle import get_bundled_wheel


class _OpenChmod:
    def __init__(
        self, path: Path, open_mode: str = "w", file_mode: int = 0o644
    ) -> None:
        self.path = path
        self.open_mode = open_mode
        self.file_mode = file_mode
        self.io: Optional[IO[Any]] = None

    def __enter__(self) -> IO[Any]:
        self.io = open(self.path, self.open_mode)
        return self.io

    def __exit__(self, type: str, value: str, traceback: str) -> None:
        self.path.chmod(self.file_mode)
        if self.io is not None:
            self.io.close()


class Creator:
    _fmt_action = "  " + green("{action:>10s}") + "    {message}"

    def __init__(
        self,
        komodo_root: Path,
        srcpath: Path,
        trackpath: Path,
        dstpath: Path,
        use_color: bool = False,
    ):
        if not use_color:
            self._fmt_action = strip_color(self._fmt_action)

        self.komodo_root = komodo_root
        self.srcpath = srcpath
        self.trackpath = trackpath
        self.dstpath = dstpath

        self.srcpy = Python(srcpath / "root/bin/python")
        self.srcpy.detect()

        self.dstpy = self.srcpy.make_dst(dstpath / "root/bin/python")

    def print_action(self, action: str, message: str) -> None:
        print(self._fmt_action.format(action=action, message=message))

    def mkdir(self, path: str) -> None:
        self.print_action("mkdir", path + "/")
        (self.dstpath / path).mkdir()

    def create_file(self, path: Union[Path, str], file_mode: int = 0o644) -> _OpenChmod:
        self.print_action("create", str(path))
        return _OpenChmod(self.dstpath / path, file_mode=file_mode)

    def remove_file(self, path: str) -> None:
        if not (self.dstpath / path).is_file():
            return

        self.print_action("remove", path)
        (self.dstpath / path).unlink()

    def venv(self) -> None:
        self.print_action("venv", "using {}".format(self.srcpy.executable))

        ld_library_path = os.environ.get("LD_LIBRARY_PATH")
        env = {"LD_LIBRARY_PATH": str(self.srcpath / "root" / "lib"), **os.environ}
        subprocess.check_output(
            [
                str(self.srcpy.executable),
                "-m",
                "venv",
                "--copies",
                str(self.dstpath / "root"),
            ],
            env=env,
        )

    def run(self, path: str) -> None:
        self.print_action("run", path)
        subprocess.check_output([str(self.dstpath / path)])

    def pip_install(self, package: str) -> None:
        pip_wheel = get_bundled_wheel("pip")
        dst_wheel = get_bundled_wheel(package)
        self.print_action("install", package)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(pip_wheel)

        subprocess.check_output(
            [
                str(self.dstpath / "root/bin/python"),
                "-m",
                "pip",
                "install",
                "--no-cache-dir",
                "--no-deps",
                "--disable-pip-version-check",
                "--no-python-version-warning",
                dst_wheel,
            ],
            env=env,
        )

    def create(self) -> None:
        self.dstpath.mkdir()

        self.venv()

        # Create komodoenv.conf
        with self.create_file("komodoenv.conf") as f:
            f.write(
                dedent(
                    f"""\
                current-release = {self.srcpath.name}
                tracked-release = {self.trackpath.name}
                mtime-release = 0
                python-version = {self.srcpy.version_info[0]}.{self.srcpy.version_info[1]}
                komodoenv-version = {get_distribution('komodoenv').version}
                komodo-root = {self.komodo_root}
                linux-dist = {distro.id() + distro.version_parts()[0]}
                """
                )
            )

        python_paths = [
            pth for pth in self.srcpy.site_paths if pth.startswith(str(self.srcpath))
        ]

        with self.create_file(
            Path("root") / self.dstpy.site_packages_path / "_komodo.pth"
        ) as f:
            print("\n".join(python_paths), file=f)

        # Create & run komodo-update
        with open(Path(__file__).parent / "update.py") as inf:
            with self.create_file(
                Path("root/bin/komodoenv-update"), file_mode=0o755
            ) as outf:
                outf.write(inf.read())
        self.run("root/bin/komodoenv-update")
        self.pip_install("setuptools")
        self.pip_install("wheel")
        self.pip_install("pip")

        self.remove_file("root/shims/komodoenv")

        if os.environ.get("SHELL", "").endswith("csh"):
            enable_script = self.dstpath / "enable.csh"
        else:
            enable_script = self.dstpath / "enable"

        print(
            dedent(
                """\

        Komodoenv has successfully been generated. You can now pip-install software.

            $ source {enable_script}
        """
            ).format(enable_script=enable_script)
        )
