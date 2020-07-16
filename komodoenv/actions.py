from pathlib import Path
from textwrap import dedent
import subprocess
import shutil
import stat
import os


class Action(object):
    priority = 0

    def __init__(self, relpath):
        self.relpath = Path(relpath)

    def start(self, ctx):
        if ctx.dry_run:
            print(str(self))
            return

        if not hasattr(self, "mkdir") or self.mkdir:
            path = (ctx.dstpath / self.relpath).parent
            if not path.exists():
                os.makedirs(str(path))

        self.install(ctx)

    def __str__(self):
        return "{:<20} {}".format(self.__class__.__name__, self.relpath)


class InstallWheel(Action):
    priority = 10  # Should happen *after* kenv has been built
    mkdir = False

    def install(self, ctx):
        ctx.pip_install(self.relpath)


class Create(Action):
    def __init__(self, relpath, contents, mode=0o644):
        super(Create, self).__init__(relpath)
        self.contents = contents
        self.mode = mode

    def install(self, ctx):
        path = str(ctx.dstpath / self.relpath)
        with open(path, "w") as f:
            f.write(self.contents)
        os.chmod(path, self.mode)


class Mkdir(Action):
    def install(self, ctx):
        (ctx.dstpath / self.relpath).mkdir()


class LibexecShim(Action):
    fmt = dedent("""\
    #!/bin/bash
    root=$(dirname $0)/..
    prog=$(basename $0)
    if [ -z "${{_KOMODO_SHIM:-}}" ]; then
      export LD_LIBRARY_PATH={komodo_prefix}/lib:{komodo_prefix}/lib64${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}
      export _KOMODO_SHIM=$prog
    fi
    $root/libexec/$prog "$@"
    """)

    def __init__(self, relpath):
        super(LibexecShim, self).__init__(relpath)

    def install(self, ctx):
        path = str(ctx.dstpath / self.relpath)
        text = self.fmt.format(komodo_prefix=(ctx.srcpath / "root"))
        with open(path, "w") as f:
            f.write(text)
        os.chmod(path, 0o755)


class EnableScript(Action):
    @property
    def fmt(self):
        raise NotImplementedError

    def install(self, ctx):
        text = self.fmt.format(
            komodo_prefix=(ctx.srcpath/"root"),
            komodo_release=ctx.srcpath.name,
            komodoenv_prefix=(ctx.dstpath/"root"),
            komodoenv_release=ctx.dstpath.name
        )
        path = str(ctx.dstpath / self.relpath)
        with open(path, "w") as f:
            f.write(text)


class EnableBash(EnableScript):
    fmt = dedent("""\
    # -*- sh -*-
    disable_komodo () {{
        if [ -n "${{_PRE_KOMODO_PATH:-}}" ]; then
            export PATH="${{_PRE_KOMODO_PATH}}"
            unset _PRE_KOMODO_PATH
        fi
        if [ -n "${{_PRE_KOMODO_MANPATH:-}}" ]; then
            export MANPATH="${{_PRE_KOMODO_MANPATH}}"
            unset _PRE_KOMODO_MANPATH
        fi
        if [ -n "${{_PRE_KOMODO_LD_LIBRARY_PATH:-}}" ]; then
            export LD_LIBRARY_PATH="${{_PRE_KOMODO_LD_LIBRARY_PATH}}"
            unset _PRE_KOMODO_LD_LIBRARY_PATH
        fi
        if [ -n "${{_PRE_KOMODO_PS1:-}}" ]; then
            export PS1="${{_PRE_KOMODO_PS1}}"
            unset _PRE_KOMODO_PS1
        fi
        if [ -n "${{BASH:-}}" -o -n "${{ZSH_VERSION:-}}" ]; then
            hash -r
        fi

        unset KOMODOENV_PREFIX
        unset KOMODOENV_RELEASE
        unset KOMODO_RELEASE
        unset ERT_LSF_SERVER

        if [ ! "${{1:-}}" = "preserve_disable_komodo" ]; then
            unset -f disable_komodo
        fi
    }}

    # unset irrelevant variables
    disable_komodo preserve_disable_komodo

    export KOMODOENV_PREFIX={komodoenv_prefix}
    export KOMODOENV_RELEASE={komodoenv_release}
    export KOMODO_RELEASE={komodo_release}

    export _PRE_KOMODO_PATH="$PATH"
    export PATH={komodoenv_prefix}/bin:{komodoenv_prefix}/shims:{komodo_prefix}/bin${{PATH:+:${{PATH}}}}

    export _PRE_KOMODO_MANPATH="$MANPATH"
    export MANPATH={komodoenv_prefix}/share/man:{komodo_prefix}/share/man:${{MANPATH}}

    export _PRE_KOMODO_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    unset LD_LIBRARY_PATH

    export _PRE_KOMODO_PS1="${{PS1:-}}"
    export PS1="(${{KOMODOENV_RELEASE}} + ${{KOMODO_RELEASE}}) ${{PS1}}"

    local_script="{komodo_prefix}/../local"
    if [ -e "$local_script" ]; then
        source "$local_script"
    fi

    if [ -n "${{BASH:-}}" -o -n "${{ZSH_VERSION:-}}" ]; then
        hash -r
    fi
    """)

    def __init__(self):
        super(EnableBash, self).__init__("enable")


class Copy(Action):
    def install(self, ctx):
        src = str(ctx.srcpath / self.relpath)
        dst = str(ctx.dstpath / self.relpath)
        shutil.copy(src, dst)


class Symlink(Action):
    def __init__(self, relpath, target=None):
        super(Symlink, self).__init__(relpath)
        self.target = target

    def install(self, ctx):
        src = self.target if self.target else ctx.srcpath / self.relpath
        dst = ctx.dstpath / self.relpath
        dst.symlink_to(src)


class Config(Action):
    fmt = dedent("""\
    base-prefix = {base_prefix}
    base-exec-prefix = {base_exec_prefix}
    base-executable = {base_executable}
    site-packages = {site_packages}
    tracked-release = {komodo_release}
    current-release = {komodo_release}
    mtime-release = 0
    """)

    def __init__(self):
        super(Config, self).__init__("komodoenv.conf")

    def install(self, ctx):
        path = str(ctx.dstpath / self.relpath)

        base_prefix = str(ctx.srcpath / "root")
        base_executable = str(ctx.srcpath / "root" / "bin" / "python")
        komodo_prefix = str(ctx.srcpath)
        site_packages = "../site-packages"

        text = self.fmt.format(
            base_prefix = base_prefix,
            base_exec_prefix = base_prefix,
            base_executable = base_executable,
            komodo_release = komodo_prefix,
            site_packages = site_packages
        )

        with open(path, "w") as f:
            f.write(text)


class UpdateScript(Action):
    """Copy and run the updater script."""
    priority = 99

    def __init__(self):
        super(UpdateScript, self).__init__("update.py")

    def install(self, ctx):
        srcpath = str(Path(__file__).parent / self.relpath)
        dstpath = str(ctx.dstpath / self.relpath)
        shutil.copy(srcpath, dstpath)
        os.chmod(dstpath, 0o755)

        subprocess.check_output([dstpath])
