from __future__ import print_function

from pathlib import Path
import subprocess
import shutil
import re
import os
from textwrap import dedent
from tempfile import mkdtemp


ENABLE_BASH = """\
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

    unset KOMODO_RELEASE
    unset ERT_LSF_SERVER

    if [ ! "${{1:-}}" = "preserve_disable_komodo" ]; then
        unset -f disable_komodo
    fi
}}

# unset irrelevant variables
disable_komodo preserve_disable_komodo

export KOMODO_RELEASE={komodoenv_prefix}

export _PRE_KOMODO_PATH="$PATH"
export PATH={komodoenv_prefix}/root/bin:{komodoenv_prefix}/root/shims${{PATH:+:${{PATH}}}}

export _PRE_KOMODO_MANPATH="$MANPATH"
export MANPATH={komodoenv_prefix}/root/share/man:{komodo_prefix}/root/share/man${{MANPATH:+:${{MANPATH}}}}

export _PRE_KOMODO_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
unset LD_LIBRARY_PATH

export _PRE_KOMODO_PS1="${{PS1:-}}"
export PS1="({komodoenv_release} + {komodo_release}) ${{PS1:-}}"

local_script="{komodo_prefix}/local"
if [ -e "$local_script" ]; then
    source "$local_script"
fi

if [ -n "${{BASH:-}}" -o -n "${{ZSH_VERSION:-}}" ]; then
    hash -r
fi
"""


def generate_enable_script(ctx, fmt):
    return fmt.format(
        komodo_prefix=ctx.srcpath,
        komodo_release=ctx.srcpath.name,
        komodoenv_prefix=ctx.dstpath,
        komodoenv_release=ctx.dstpath.name,
    )


def create_enable_scripts(ctx):
    with open(str(ctx.dstpath / "enable"), "w") as f:
        f.write(generate_enable_script(ctx, ENABLE_BASH))
    with open(str(ctx.dstpath / "enable.csh"), "w") as f:
        pass


def create_virtualenv(ctx):
    tmpdir = mkdtemp(prefix="komodoenv.")

    from virtualenv import cli_run

    ld_library_path = os.environ.get("LD_LIBRARY_PATH")
    os.environ["LD_LIBRARY_PATH"] = str(ctx.srcpath / "root" / "lib")
    cli_run(
        [
            "--python",
            str(ctx.src_python_path),
            "--app-data",
            tmpdir,
            "--always-copy",
            str(ctx.dstpath / "root"),
        ],
    )
    if ld_library_path is None:
        del os.environ["LD_LIBRARY_PATH"]
    else:
        os.environ["LD_LIBRARY_PATH"] = ld_library_path


def copy_update_script(ctx):
    srcpath = str(Path(__file__).parent / "update.py")
    dstpath = str(ctx.dstpath / "komodo-update")
    shutil.copy(srcpath, dstpath)
    os.chmod(dstpath, 0o755)

    subprocess.check_output([dstpath])


def create_config(ctx):
    with open(str(ctx.dstpath / "komodoenv.conf"), "w") as f:
        f.write(
            dedent(
                """\
        current-release = {rel}
        tracked-release = {rel}
        mtime-release = 0
        """
            ).format(rel=ctx.srcpath.name)
        )


def create_pth(ctx):
    python_paths = [
        pth for pth in ctx.src_python_paths if pth.startswith(str(ctx.srcpath))
    ]

    with open(str(ctx.dst_python_libpath / "site-packages" / "_komodo.pth"), "w") as f:
        print("\n".join(python_paths), file=f)


def shim_pythons(ctx):
    pattern = re.compile("^python[0-9.]*$")
    (ctx.dstpath / "root" / "libexec").mkdir()

    txt = dedent(
        """\
    #!/bin/bash
    export LD_LIBRARY_PATH={komodo_root}/lib:{komodo_root}/lib64${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}
    exec -a "$0" "{komodoenv_root}/libexec/$(basename $0)" "$@"
    """
    ).format(komodo_root=(ctx.srcpath / "root"), komodoenv_root=(ctx.dstpath / "root"))

    for name in os.listdir(str(ctx.dstpath / "root" / "bin")):
        if not pattern.match(name):
            continue

        binpath = str(ctx.dstpath / "root" / "bin" / name)
        libexecpath = str(ctx.dstpath / "root" / "libexec" / name)

        shutil.copy(binpath, libexecpath)
        with open(binpath, "w") as f:
            f.write(txt)
        os.chmod(binpath, 0o755)


def create(ctx):
    ctx.dstpath.mkdir()
    create_virtualenv(ctx)
    create_enable_scripts(ctx)
    create_config(ctx)
    create_pth(ctx)
    shim_pythons(ctx)
    copy_update_script(ctx)
