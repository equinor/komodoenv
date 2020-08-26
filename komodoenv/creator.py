from __future__ import print_function

from pathlib import Path
import subprocess
import shutil
import re
import os
import platform
import sys
import logging
from textwrap import dedent
from tempfile import mkdtemp
from colors import green, strip_color
from pkg_resources import get_distribution

from komodoenv.python import Python


class _OpenChmod(object):
    def __init__(self, path, open_mode="w", file_mode=0o644):
        self.path = path
        self.open_mode = open_mode
        self.file_mode = file_mode
        self.io = None

    def __enter__(self):
        self.io = open(self.path, self.open_mode)
        return self.io

    def __exit__(self, type, value, traceback):
        self.path.chmod(self.file_mode)
        self.io.close()


class Creator(object):
    _fmt_action = "  " + green("{action:>10s}") + "    {message}"

    def __init__(self, komodo_root, srcpath, dstpath=None, use_color=False):
        if not use_color:
            self._fmt_action = strip_color(self._fmt_action)

        self.komodo_root = komodo_root
        self.srcpath = srcpath
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
        return _OpenChmod(self.dstpath / path, file_mode=file_mode)

    def remove_file(self, path):
        if not (self.dstpath / path).is_file():
            return

        self.print_action("remove", path)
        (self.dstpath / path).unlink()

    def virtualenv(self):
        self.print_action("virtualenv", "using {}".format(self.srcpy.executable))

        tmpdir = mkdtemp(prefix="komodoenv.")

        from virtualenv import cli_run

        ld_library_path = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = str(self.srcpath / "root" / "lib")
        cli_run(
            [
                "--python",
                str(self.srcpy.executable),
                "--app-data",
                tmpdir,
                "--activators=",  # Don't generate any activate scripts
                "--always-copy",
                str(self.dstpath / "root"),
            ],
        )
        if ld_library_path is None:
            del os.environ["LD_LIBRARY_PATH"]
        else:
            os.environ["LD_LIBRARY_PATH"] = ld_library_path

    def run(self, path):
        self.print_action("run", path)
        subprocess.check_output([str(self.dstpath / path)])

    def shim_pythons(self):
        pattern = re.compile("^python[0-9.]*$")

        txt = dedent(
            """\
        #!/bin/bash
        export LD_LIBRARY_PATH={komodo_root}/lib:{komodo_root}/lib64${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}
        exec -a "$0" "{komodoenv_root}/libexec/$(basename $0)" "$@"
        """
        ).format(
            komodo_root=(self.srcpath / "root"), komodoenv_root=(self.dstpath / "root")
        )

        self.mkdir("root/libexec")
        for name in os.listdir(str(self.dstpath / "root" / "bin")):
            if not pattern.match(name):
                continue

            srcpath = "root/bin/" + name
            dstpath = "root/libexec/" + name

            self.print_action("copy", "{} -> {}".format(srcpath, dstpath))
            shutil.copy(self.dstpath / srcpath, self.dstpath / dstpath)
            with self.create_file(srcpath, file_mode=0o755) as f:
                f.write(txt)

    def create(self):
        self.dstpath.mkdir()

        self.virtualenv()

        # Create komodoenv.conf
        with self.create_file("komodoenv.conf") as f:
            f.write(
                dedent(
                    """\
                current-release = {rel}
                tracked-release = {rel}
                mtime-release = 0
                python-version = {maj}.{min}
                komodoenv-version = {ver}
                komodo-root = {root}
                linux-dist = {dist}
                """
                ).format(
                    rel=self.srcpath.name,
                    maj=self.srcpy.version_info[0],
                    min=self.srcpy.version_info[1],
                    ver=get_distribution("komodoenv").version,
                    root=self.komodo_root,
                    dist="-".join(platform.dist() if hasattr(platform, "dist") else "none")
                )
            )

        python_paths = [
            pth for pth in self.srcpy.site_paths if pth.startswith(str(self.srcpath))
        ]

        with self.create_file(
            Path("root") / self.dstpy.site_packages_path / "_komodo.pth"
        ) as f:
            print("\n".join(python_paths), file=f)

        # Create shims
        self.shim_pythons()

        # Create & run komodo-update
        with open(Path(__file__).parent / "update.py") as inf:
            with self.create_file(
                Path("root/bin/komodoenv-update"), file_mode=0o755
            ) as outf:
                outf.write(inf.read())
        self.run("root/bin/komodoenv-update")

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
