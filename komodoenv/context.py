import os
import json
from subprocess import PIPE, Popen
from enum import Enum
from komodoenv.bundle import get_embed_wheels


class KomodoType(Enum):
    UNKNOWN = 0  # Probably a test
    REAL = 1
    SHIM = 2
    VENV = 3


class Context(object):
    def __init__(self, srcpath, dstpath=None):
        self.srcpath = srcpath
        self.dstpath = dstpath
        self.dry_run = False

        bin_python = (self.srcpath / "root" / "bin" / "python")
        if not bin_python.exists():
            # Probably constructed in a test. Ignore this until sometime later
            # in the process when we will inevitably fail.
            self.type = KomodoType.UNKNOWN
            return

        # Get python version_info
        script = "import sys,json;print(json.dumps(sys.version_info[:]))"
        env = {
            "LD_LIBRARY_PATH": "{0}/lib:{0}/lib64".format(self.srcpath / "root")
        }
        self.version_info = json.loads(self.invoke_srcpython(script=script, env=env))

        # Existence of libexec suggests that this is a libexec-shim komodo release
        libexec_python = (self.srcpath / "root" / "libexec" / "python")
        if libexec_python.exists():
            self.type = KomodoType.SHIM
            return

        # Existence of any libpythons suggests that this is a normal Python
        # install (compiled from sources)
        for libdir in "lib", "lib64":
            for suffix in "", "m", "dm":
                name = "libpython{}.{}{}.so".format(
                    self.version_info[0],
                    self.version_info[1],
                    suffix
                )

                if (self.srcpath / "root" / libdir / name).exists():
                    self.type = KomodoType.REAL
                    return

        # Otherwise this is most likely a virtualenv
        self.type = KomodoType.VENV

    def pip_install(self, package):
        package = str(package)

        wheels = get_embed_wheels(self.version_info)

        env = {
            "PYTHONPATH": str(wheels["pip"]),
        }

        self.invoke_dstpython(["-m", "pip", "-q", "install", "--only-binary", ":all:", "--disable-pip-version-check","--no-python-version-warning", "--no-index", str(wheels[package])], env=env)

    def invoke_srcpython(self, args=None, env=None, script=None):
        pyexec = self.srcpath / "root" / "bin" / "python"
        return self.invoke_python(pyexec, args, env, script)

    def invoke_dstpython(self, args=None, env=None, script=None):
        pyexec = self.dstpath / "root" / "bin" / "python"
        return self.invoke_python(pyexec, args, env, script)

    def invoke_python(self, python_executable, args = None, env=None, script=None):
        if args is None:
            args = []
        if env is None:
            env = {}
        if script is not None:
            # Prepend '-' to tell Python to read from stdin
            args = ["-"] + args

        env["PATH"] = "{}:{}".format(python_executable.parent.absolute(), os.environ["PATH"])
        env["LD_LIBRARY_PATH"] = "{0}/lib:{0}/lib64".format(str(self.srcpath / "root"))

        args = [python_executable] + args
        proc = Popen(map(str, args), stdin=PIPE, stdout=PIPE, env=env)
        stdout, _ =  proc.communicate(script)

        return stdout
