import os
import subprocess
from contextlib import contextmanager
from importlib.metadata import distribution
from pathlib import Path
from textwrap import dedent

import distro

from komodoenv.bundle import get_bundled_wheel
from komodoenv.colors import green, strip_color
from komodoenv.python import Python


@contextmanager
def open_chmod(path: Path, mode: str = "w", file_mode=0o644):
    with open(path, mode, encoding="utf-8") as file:
        yield file
    path.chmod(file_mode)


class Creator:
    _fmt_action = "  " + green("{action:>10s}") + "    {message}"

    def __init__(
        self,
        *,
        komodo_root,
        srcpath,
        trackpath,
        dstpath=None,
        use_color=False,
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

    def print_action(self, action, message):
        print(self._fmt_action.format(action=action, message=message))

    def mkdir(self, path):
        self.print_action("mkdir", path + "/")
        (self.dstpath / path).mkdir()

    def create_file(self, path, file_mode=0o644):
        self.print_action("create", path)
        return open_chmod(self.dstpath / path, file_mode=file_mode)

    def remove_file(self, path):
        if not (self.dstpath / path).is_file():
            return

        self.print_action("remove", path)
        (self.dstpath / path).unlink()

    def venv(self):
        self.print_action("venv", f"using {self.srcpy.executable}")

        env = {"LD_LIBRARY_PATH": str(self.srcpath / "root" / "lib"), **os.environ}
        subprocess.check_output(
            [
                str(self.srcpy.executable)
                + str(self.srcpy.version_info[0])
                + "."
                + str(self.srcpy.version_info[1]),
                "-m",
                "venv",
                "--copies",
                str(self.dstpath / "root"),
            ],
            env=env,
        )

    def run(self, path):
        self.print_action("run", path)
        subprocess.check_output([str(self.dstpath / path)])

    def pip_install(self, package: str) -> None:
        pip_wheel = get_bundled_wheel("pip")
        dst_wheel = get_bundled_wheel(package)
        self.print_action("install", package)

        env = os.environ.copy()
        env["PYTHONPATH"] = pip_wheel

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

    def create(self):
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
                komodoenv-version = {distribution('komodoenv').version}
                komodo-root = {self.komodo_root}
                linux-dist = {distro.id() + distro.version_parts()[0]}
                """,
                ),
            )

        python_paths = [
            pth for pth in self.srcpy.site_paths if pth.startswith(str(self.srcpath))
        ]

        # We use zzz_komodo.pth to try and make it the last .pth file to be processed
        # alphabetically, and thus allowing for other editable installs to 'overwrite'
        # komodo packages.
        with self.create_file(
            Path("root") / self.dstpy.site_packages_path / "zzz_komodo.pth",
        ) as f:
            print("\n".join(python_paths), file=f)

        # Create & run komodo-update
        with open(
            Path(__file__).parent / "update.py",
            encoding="utf-8",
        ) as inf, self.create_file(
            Path("root/bin/komodoenv-update"),
            file_mode=0o755,
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
                f"""\

        Komodoenv has successfully been generated. You can now pip-install software.

            $ source {enable_script}
        """,
            ),
        )
