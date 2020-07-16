from pathlib import Path
import subprocess
import six
import shutil
import re
from textwrap import dedent
from komodoenv import actions


PYTHON_PATTERN = re.compile("^python[0-9.]*$")


class BaseCreator(object):
    MODULE_TESTS = ("{}.so", "{}module.so", "{}.py", "{}.pyc", "{}")

    def __init__(self, ctx):
        self.ctx = ctx

    def create(self):
        pass

    def get_actions(self):

        acts = [
            actions.EnableBash(),
            actions.Mkdir(Path("root")/"lib"/self.libdir/"site-packages"),
            #actions.Symlink("root/lib64", "lib"),
            actions.InstallWheel("pip"),
            actions.InstallWheel("setuptools"),
            actions.InstallWheel("wheel"),
            actions.Config(),
            actions.UpdateScript()
        ]

        acts.extend(self.get_bin_actions())
        acts.extend(self.get_symlink_actions())
        acts.extend(self.get_extra_actions())

        # Group by priority
        groups = {}
        for act in acts:
            p = act.priority
            if p not in groups:
                groups[p] = [act]
            else:
                groups[p].append(act)

        # Sort and flatten
        return [
            act
            for group in groups.values()
            for act in sorted(group, key=lambda x: str(x.relpath))
        ]

    def get_bin_actions(self):
        for srcpath in (self.srcpath / "root" / "libexec").glob("*"):
            rel = srcpath.relative_to(self.srcpath)
            if not PYTHON_PATTERN.match(rel.name):
                continue
            yield actions.Copy(rel)
            yield actions.LibexecShim("root/bin/{}".format(rel.name))

    def get_symlink_actions(self):
        for file_ in self.required_files:
            srcpath = self.srcpylib / file_
            if not srcpath.exists():
                raise ValueError("File not found: {}".format(srcpath))
            yield actions.Symlink(srcpath.relative_to(self.srcpath))

        for module in self.required_modules:
            for fmt in self.MODULE_TESTS:
                srcpath = self.srcpylib / fmt.format(module)
                if srcpath.exists():
                    yield actions.Symlink(srcpath.relative_to(self.srcpath))

    def get_extra_actions(self):
        """Any additional actions that need to be taken. Eg, generate site.py"""
        return []

    @property
    def srcpath(self):
        return self.ctx.srcpath

    @property
    def srcpylib(self):
        """Absolute path to source's lib/pythonX.Y"""
        return self.srcpath / "root" / "lib" / self.libdir

    @property
    def dstpath(self):
        return self.ctx.dstpath

    @property
    def dstpylib(self):
        """Absolute path to destination's lib/pythonX.Y"""
        return self.dstpath / "root" / "lib" / self.libdir

    @property
    def libdir(self):
        """Name of the python libdir. Eg, for CPython27, it's 'python2.7'"""
        raise NotImplementedError

    @property
    def required_modules(self):
        """List of Python modules in lib/pythonX.Y that must be symlinked to"""
        raise NotImplementedError

    @property
    def required_files(self):
        """List of files in lib/pythonX.Y that must be symlinked"""
        raise NotImplementedError

    def _create_enable_script(self):
        bash_script = textwrap.dedent()

    def _create_directory_structure(self):
        dst = self.dstpath / "root"

        (dst/"bin").mkdir_p()
        (dst/"libexec").mkdir_p()
        (dst/"lib"/self.libdir/"site-packages").mkdir_p()
        (dst/"lib64").symlink_to("lib")

    def _symlink_required_modules(self):
        pass

    def srcpyexec(self, script=None, env=None):
        pass

    def _pyexec_get_sys(self, syscmd):
        self._pyexec()

    def _pyexec(self, python_exec, args=None, script=None, env=None):
        if args is None:
            args = []
        if script is not None:
            args = ["-"] + args
        if env is None:
            env = {}

        env["LD_LIBRARY_PATH"] = "{0}/lib:{0}/lib64".format(self.srcpath)
        proc = subprocess.Popen([python_exec] + args, env=env, stdout=subprocess.PIPE)

        stdout, _ = proc.communicate(script)
        return six.ensure_str(stdout)
