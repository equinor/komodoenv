import os
import subprocess
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from importlib.metadata import distribution
from pathlib import Path
from textwrap import dedent
from typing import IO

import distro

from komodoenv.bundle import get_bundled_wheel
from komodoenv.colors import green, strip_color
from komodoenv.python import Python
from komodoenv.update import pth_content


@contextmanager
def open_chmod(
    path: Path, mode: str = "w", file_mode: int = 0o644
) -> Iterator[IO[str]]:
    with open(path, mode, encoding="utf-8") as file:
        yield file
    path.chmod(file_mode)


class Creator:
    _fmt_action = "  " + green("{action:>10s}") + "    {message}"

    def __init__(
        self,
        *,
        komodo_root: Path,
        srcpath: Path,
        trackpath: Path,
        dstpath: Path,
        use_color: bool = False,
    ) -> None:
        if not use_color:
            self._fmt_action = strip_color(self._fmt_action)

        self.komodo_root = komodo_root
        self.srcpath = srcpath
        self.trackpath = trackpath
        self.dstpath = dstpath

        self.srcpy = Python(srcpath / "root/bin/python")
        self.srcpy.detect()

        self.dstpy = self.srcpy.make_dst(dstpath / "root/bin/python")

    def print_action(self, action: str, message: str | Path) -> None:
        print(self._fmt_action.format(action=action, message=message))

    def mkdir(self, path: str) -> None:
        self.print_action("mkdir", path + "/")
        (self.dstpath / path).mkdir()

    def create_file(
        self, path: str | Path, file_mode: int = 0o644
    ) -> AbstractContextManager[IO[str]]:
        self.print_action("create", path)
        return open_chmod(self.dstpath / path, file_mode=file_mode)

    def remove_file(self, path: str | Path) -> None:
        if not (self.dstpath / path).is_file():
            return

        self.print_action("remove", path)
        (self.dstpath / path).unlink()

    def venv(self) -> None:
        self.print_action("venv", f"using {self.srcpy.executable}")

        env = {"LD_LIBRARY_PATH": str(self.srcpath / "root" / "lib"), **os.environ}
        subprocess.check_output(
            [
                f"{self.srcpy.executable}{self.srcpy.version}",
                "-m",
                "venv",
                "--copies",
                "--without-pip",
                str(self.dstpath / "root"),
            ],
            env=env,
        )

    def run(self, path: str | Path) -> None:
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
                python-version = {self.srcpy.version}
                komodoenv-version = {distribution("komodoenv").version}
                komodo-root = {self.komodo_root}
                linux-dist = {distro.id() + distro.version_parts()[0]}
                """,
                ),
            )

        python_paths = [
            pth for pth in self.srcpy.site_paths if pth.startswith(str(self.srcpath))
        ]

        finder = Path(__file__).parent / "editable_finder.py"
        with self.create_file(
            self.dstpy.site_packages_path / "_komodo_editable_finder.py",
        ) as f:
            f.write(finder.read_text(encoding="utf-8"))

        # We use zzz_komodo.pth to try and make it the last .pth file to be processed
        # alphabetically, and thus allowing for other editable installs to 'overwrite'
        # komodo packages.
        with self.create_file(
            self.dstpy.site_packages_path / "zzz_komodo.pth",
        ) as f:
            f.write(pth_content(python_paths))

        # Create & run komodo-update
        with (
            open(
                Path(__file__).parent / "update.py",
                encoding="utf-8",
            ) as inf,
            self.create_file(
                Path("root/bin/komodoenv-update"),
                file_mode=0o755,
            ) as outf,
        ):
            outf.write(inf.read())
        self.run("root/bin/komodoenv-update")
        self.pip_install("pip")

        self.remove_file("root/shims/komodoenv")

        if os.environ.get("SHELL", "").endswith("csh"):
            enable_script = self.dstpath / "enable.csh"
        else:
            enable_script = self.dstpath / "enable"

        print(
            dedent(
                f"""\

        Komodoenv has successfully been generated. You can now pip-install software.

            $ source {enable_script}
        """,
            ),
        )
