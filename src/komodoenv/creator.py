from __future__ import annotations

import os
import subprocess
from contextlib import _GeneratorContextManager, contextmanager
from importlib.metadata import distribution
from pathlib import Path
from textwrap import dedent
from typing import IO, TYPE_CHECKING, Any

import distro

from komodoenv.bundle import get_bundled_wheel
from komodoenv.colors import green, strip_color
from komodoenv.python import Python

if TYPE_CHECKING:
    from collections.abc import Generator


@contextmanager
def open_chmod(
    path: Path, mode: str = "w", file_mode: int = 0o644
) -> Generator[IO[Any], Any, None]:
    with open(path, mode, encoding="utf-8") as file:
        yield file
    path.chmod(file_mode)


class Creator:
    _fmt_action = "  " + green("{action:>10s}") + "    {message}"

    def __init__(
        self,
        *,
        komodo_root: Path,
        src_path: Path,
        track_path: Path,
        dst_path: Path,
        use_color: bool = False,
    ) -> None:
        if not use_color:
            self._fmt_action = strip_color(self._fmt_action)

        self.komodo_root = komodo_root
        self.src_path = src_path
        self.track_path = track_path
        self.dst_path = dst_path

        self.srcpy = Python(src_path / "root/bin/python")
        self.srcpy.detect()

        self.dstpy = self.srcpy.make_dst(dst_path / "root/bin/python")

    def print_action(self, action: str, message: str) -> None:
        print(self._fmt_action.format(action=action, message=message))

    def create_file(
        self, path: Path | str, file_mode: int = 0o644
    ) -> _GeneratorContextManager[IO[Any]]:
        self.print_action("create", str(path))
        return open_chmod(self.dst_path / path, file_mode=file_mode)

    def remove_file(self, path: Path) -> None:
        if not (self.dst_path / path).is_file():
            return

        self.print_action("remove", str(path))
        (self.dst_path / path).unlink()

    def venv(self) -> None:
        self.print_action("venv", f"using {self.srcpy.executable}")

        env = {"LD_LIBRARY_PATH": str(self.src_path / "root" / "lib"), **os.environ}
        subprocess.check_output(
            [
                str(self.srcpy.executable)
                + str(self.srcpy.version_info[0])
                + "."
                + str(self.srcpy.version_info[1]),
                "-m",
                "venv",
                "--copies",
                "--without-pip",
                str(self.dst_path / "root"),
            ],
            env=env,
        )

    def run(self, path: Path) -> None:
        self.print_action("run", str(path))
        subprocess.check_output([str(self.dst_path / path)])

    def pip_install(self, package: str) -> None:
        pip_wheel = get_bundled_wheel("pip")
        dst_wheel = get_bundled_wheel(package)
        self.print_action("install", package)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(pip_wheel)

        subprocess.check_output(
            [
                str(self.dst_path / "root/bin/python"),
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
        self.dst_path.mkdir()

        self.venv()

        # Create komodoenv.conf
        with self.create_file("komodoenv.conf") as f:
            f.write(
                dedent(
                    f"""\
                current-release = {self.src_path.name}
                tracked-release = {self.track_path.name}
                mtime-release = 0
                python-version = {self.srcpy.version_info[0]}.{self.srcpy.version_info[1]}
                komodoenv-version = {distribution("komodoenv").version}
                komodo-root = {self.komodo_root}
                linux-dist = {distro.id() + distro.version_parts()[0]}
                """,
                ),
            )

        python_paths = [
            pth for pth in self.srcpy.site_paths if pth.startswith(str(self.src_path))
        ]

        # We use zzz_komodo.pth to try and make it the last .pth file to be processed
        # alphabetically, and thus allowing for other editable installs to 'overwrite'
        # komodo packages.
        with self.create_file(
            Path("root") / self.dstpy.site_packages_path / "zzz_komodo.pth",
        ) as f:
            print("\n".join(python_paths), file=f)

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
        self.run(Path("root/bin/komodoenv-update"))
        self.pip_install("pip")

        self.remove_file(Path("root/shims/komodoenv"))

        if os.environ.get("SHELL", "").endswith("csh"):
            enable_script = self.dst_path / "enable.csh"
        else:
            enable_script = self.dst_path / "enable"

        print(
            dedent(
                f"""\

        Komodoenv has successfully been generated. You can now pip-install software.

            $ source {enable_script}
        """,
            ),
        )
