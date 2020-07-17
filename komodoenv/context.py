import os
import json
from pathlib import Path
from subprocess import PIPE, Popen
from enum import Enum


class KomodoType(Enum):
    UNKNOWN = 0  # Probably a test
    REAL = 1
    SHIM = 2
    VENV = 3


class Context(object):
    def __init__(self, srcpath, dstpath=None):
        self.srcpath = Path(srcpath)
        self.dstpath = dstpath
        self.dry_run = False

        bin_python = self.srcpath / "root" / "bin" / "python"
        if not bin_python.exists():
            # Probably constructed in a test. Ignore this until sometime later
            # in the process when we will inevitably fail.
            self.type = KomodoType.UNKNOWN
            return

        # Get python version_info
        script = b"import sys,json;print(json.dumps(sys.version_info[:]))"
        env = {"LD_LIBRARY_PATH": "{0}/lib:{0}/lib64".format(self.srcpath / "root")}
        self.version_info = json.loads(self.invoke_srcpython(script=script, env=env))

        # Get python sys.path
        script = b"import sys,json;print(json.dumps(sys.path))"
        env = {"LD_LIBRARY_PATH": "{0}/lib:{0}/lib64".format(self.srcpath / "root")}
        self.src_python_paths = json.loads(
            self.invoke_srcpython(script=script, env=env)
        )

        # Existence of libexec suggests that this is a libexec-shim komodo release
        libexec_python = self.srcpath / "root" / "libexec" / "python"
        if libexec_python.exists():
            self.type = KomodoType.SHIM
            return

        # Existence of any libpythons suggests that this is a normal Python
        # install (compiled from sources)
        for libdir in "lib", "lib64":
            for suffix in "", "m", "dm":
                name = "libpython{}.{}{}.so".format(
                    self.version_info[0], self.version_info[1], suffix
                )

                if (self.srcpath / "root" / libdir / name).exists():
                    self.type = KomodoType.REAL
                    return

        # Otherwise this is most likely a virtualenv
        self.type = KomodoType.VENV

    def invoke_srcpython(self, args=None, env=None, script=None):
        pyexec = self.srcpath / "root" / "bin" / "python"
        return self.invoke_python(pyexec, args, env, script)

    def invoke_dstpython(self, args=None, env=None, script=None):
        pyexec = self.dstpath / "root" / "bin" / "python"
        return self.invoke_python(pyexec, args, env, script)

    def invoke_python(self, python_executable, args=None, env=None, script=None):
        if args is None:
            args = []
        if env is None:
            env = {}
        if script is not None:
            # Prepend '-' to tell Python to read from stdin
            args = ["-"] + args

        python_executable = Path(python_executable)

        env["PATH"] = "{}:{}".format(
            python_executable.parent.absolute(), os.environ["PATH"]
        )
        env["LD_LIBRARY_PATH"] = "{0}/lib:{0}/lib64".format(str(self.srcpath / "root"))

        args = [python_executable] + args
        proc = Popen(map(str, args), stdin=PIPE, stdout=PIPE, env=env)
        stdout, _ = proc.communicate(script)

        return stdout

    @property
    def src_python_path(self):
        return self.srcpath / "root" / "bin" / "python"

    @property
    def dst_python_libpath(self):
        libdir = "python{}.{}".format(self.version_info[0], self.version_info[1])
        return self.dstpath / "root" / "lib" / libdir
