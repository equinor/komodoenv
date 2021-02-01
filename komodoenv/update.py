#!/usr/bin/python3
"""
This is the update mechanism for komodo.

Note: This script must be kept compatible with Python 3.6 as long as RHEL7 is
alive and kicking. The reason for this is that we wish to use /usr/bin/python3
to avoid any dependency on komodo during the update.
"""
import os
import re
import sys
import shutil
from typing import List
from argparse import ArgumentParser
from textwrap import dedent


try:
    from distro import id as distro_id, version_parts as distro_versions
except ImportError:
    # The 'distro' package isn't installed. Pretend we're on RHEL7.
    #
    # yum install python36-distro
    def distro_id():
        return "rhel"

    def distro_versions():
        return ("7", "0", "0")


ENABLE_BASH = """\
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

export _PRE_KOMODO_MANPATH="${{MANPATH:-}}"
export MANPATH={komodoenv_prefix}/root/share/man:{komodo_prefix}/root/share/man${{MANPATH:+:${{MANPATH}}}}

export _PRE_KOMODO_LD_LIBRARY_PATH="${{LD_LIBRARY_PATH:-}}"
export LD_LIBRARY_PATH={komodo_prefix}/root/lib:{komodo_prefix}/lib64${{LD_LIBRARY_PATH:+${{LD_LIBRARY_PATH}}}}

export _PRE_KOMODO_PS1="${{PS1:-}}"
export PS1="({komodoenv_release} + {komodo_release}) ${{PS1:-}}"

local_script="{komodo_prefix}/local"
if [ -e "$local_script" ]; then
    source "$local_script"
fi

if [ -n "${{BASH:-}}" -o -n "${{ZSH_VERSION:-}}" ]; then
    hash -r
fi

if [ -d {komodo_prefix}/motd/scripts ]
then
    for f in {komodo_prefix}/motd/scripts/*
    do
        $f
    done
fi

if [ -d {komodo_prefix}/motd/messages ]
then
    cat {komodo_prefix}/motd/messages/*
fi

{komodoenv_prefix}/root/bin/komodoenv-update --check
"""


ENABLE_CSH = """\
alias disable_komodo '\\\\
    test $?_PRE_KOMODO_PATH != 0 && setenv PATH "$_PRE_KOMODO_PATH" && unsetenv _PRE_KOMODO_PATH;\\\\
    test $?_PRE_KOMODO_MANPATH != 0 && setenv MANPATH "$_PRE_KOMODO_MANPATH" && unsetenv _PRE_KOMODO_MANPATH;\\\\
    test $?_PRE_KOMODO_LD_PATH != 0 && setenv LD_LIBRARY_PATH "$_PRE_KOMODO_LD_PATH" && unsetenv _PRE_KOMODO_LD_PATH;\\\\
    test $?_KOMODO_OLD_PROMPT != 0 && set prompt="$_KOMODO_OLD_PROMPT" && unsetenv _KOMODO_OLD_PROMPT;\\\\
    test "\\!:*" != "preserve_disable_komodo" && unalias disable_komodo;\\\\
    unsetenv KOMODO_RELEASE;\\\\
    unsetenv ERT_LSF_SERVER;\\\\
    rehash;\\\\
    '
rehash
disable_komodo preserve_disable_komodo

if $?PATH then
    setenv _PRE_KOMODO_PATH "$PATH"
    setenv PATH {komodoenv_prefix}/root/bin:{komodoenv_prefix}/root/shims:$PATH
else
    setenv PATH {komodoenv_prefix}/root/bin:{komodoenv_prefix}/root/shims
endif

if $?MANPATH then
    setenv _PRE_KOMODO_MANPATH "$MANPATH"
    setenv MANPATH {komodoenv_prefix}/root/share/man:{komodo_prefix}/root/share/man:$MANPATH
else
    setenv MANPATH {komodoenv_prefix}/root/share/man:{komodo_prefix}/root/share/man:
endif

if $?LD_LIBRARY_PATH then
    setenv _PRE_KOMODO_LD_PATH "$LD_LIBRARY_PATH"
    setenv LD_LIBRARY_PATH {komodo_prefix}/root/lib:{komodo_prefix}/root/lib64:$LD_LIBRARY_PATH
else
    setenv LD_LIBRARY_PATH {komodo_prefix}/root/lib:{komodo_prefix}/root/lib64
endif

setenv KOMODO_RELEASE {komodoenv_prefix}

set local_script={komodo_prefix}/local.csh
if ( -r $local_script) then
    source $local_script
endif

# Could be in a non-interactive environment,
# in which case, $prompt is undefined and we wouldn't
# care about the prompt anyway.
if ( $?prompt ) then
    setenv _KOMODO_OLD_PROMPT "$prompt"
    set prompt = "[{komodoenv_release} + {komodo_release}] $prompt"
endif

rehash

if ( -d {komodo_prefix}/motd/scripts ) then
    foreach f ({komodo_prefix}/motd/scripts/*)
        $f
    end
endif

if ( -d {komodo_prefix}/motd/messages ) then
    cat {komodo_prefix}/motd/messages/*
endif

{komodoenv_prefix}/root/bin/komodoenv-update --check
"""


def read_config() -> dict:
    with open(
        os.path.join(os.path.dirname(__file__), "..", "..", "komodoenv.conf")
    ) as f:
        lines = f.readlines()
    config = {}
    for line in lines:
        try:
            split_at = line.index("=")
        except ValueError:
            continue
        else:
            key = line[:split_at].strip()
            val = line[split_at + 1 :].strip()
            config[key] = val

    if "komodo-root" not in config:
        config["komodo-root"] = "/prog/res/komodo"

    return config


def rhel_version_suffix() -> str:
    """
    Return the current running RHEL version as "-rhelX" where X is the major
    version. "" if not on RHEL.
    """
    return "-" + distro_id() + distro_versions()[0]


def check_same_distro(config: dict):
    """Python might not run properly on a different distro than the one that
    komodoenv was first generated for. Returns True if the distro in the config
    matches ours, False otherwise.

    """
    confdist = config.get("linux-dist", "")
    thisdist = distro_id() + distro_versions()[0]
    if confdist == thisdist:
        return

    sys.stderr.write(
        "Warning: Current distribution '{current}' doesn't match the one that "
        "was used to generate this environment '{config}'. You might need to "
        "recreate this komodoenv\n".format(current=thisdist, config=confdist)
    )


def get_pkg_version(
    config: dict, srcpath: str, package: str = "komodoenv"
) -> List[str]:
    """Locate `package`'s version in the current komodo distribution. This format is
    defined in PEP 376 "Database of Installed Python Distributions".

    Returns None if package wasn't found.
    """
    pkgdir = os.path.join(
        srcpath, "lib", "python" + config["python-version"], "site-packages"
    )
    pattern = re.compile("^{}-(.+).dist-info".format(package))

    matches = []
    for name in os.listdir(pkgdir):
        match = pattern.match(name)
        if match is not None:
            matches.append(match[1])
    if len(matches) > 0:
        return max(matches)


def can_update(config: dict) -> bool:
    """Compares the version of komodoenv that built the release with the one in the
    one we want to update to. If the major versions are the same, we know the
    layout is identical, and can be safely updated with this script.

    """
    version = get_pkg_version(
        config, os.path.join(config["komodo-root"], config["tracked-release"], "root")
    )
    if "komodoenv-version" not in config or version is None:
        return False

    current_maj = int(config["komodoenv-version"].split(".")[0])
    updated_maj = int(version.split(".")[0])

    return current_maj == updated_maj


def write_config(config: dict):
    with open(
        os.path.join(os.path.dirname(__file__), "..", "..", "komodoenv.conf"), "w"
    ) as f:
        for key, val in config.items():
            f.write("{key} = {val}\n".format(key=key, val=val))


def current_track(config: dict) -> dict:
    path = os.path.join(config["komodo-root"], config["tracked-release"])

    rp = os.path.realpath(path)
    st = os.stat(path)

    config = {
        "tracked-release": config["tracked-release"],
        "current-release": os.path.basename(rp),
        "mtime-release": str(st.st_mtime),
    }

    return config


def should_update(config: dict, current: dict) -> bool:
    return any(
        [
            config[x] != current[x]
            for x in ("tracked-release", "current-release", "mtime-release")
        ]
    )


def enable_script(fmt: str, komodo_prefix: str, komodoenv_prefix: str):
    return fmt.format(
        komodo_prefix=komodo_prefix,
        komodo_release=os.path.basename(komodo_prefix),
        komodoenv_prefix=komodoenv_prefix,
        komodoenv_release=os.path.basename(komodoenv_prefix),
    )


def update_enable_script(komodo_prefix: str, komodoenv_prefix: str):
    with open(os.path.join(komodoenv_prefix, "enable"), "w") as f:
        f.write(enable_script(ENABLE_BASH, komodo_prefix, komodoenv_prefix))
    with open(os.path.join(komodoenv_prefix, "enable.csh"), "w") as f:
        f.write(enable_script(ENABLE_CSH, komodo_prefix, komodoenv_prefix))


def rewrite_executable(path: str, python: str, text: bytes):
    path = os.path.realpath(path)
    root = os.path.realpath(os.path.join(path, "..", ".."))
    libs = os.pathsep.join((os.path.join(root, "lib"), os.path.join(root, "lib64")))

    newline_pos = text.find(b"\n")
    if (
        text[:2] == b"#!"
        and newline_pos >= 0
        and text[:newline_pos].find(b"python") >= 0
    ):
        return b"#!" + python.encode("utf8") + text[newline_pos:]

    return (
        dedent(
            """\
    #!/bin/bash
    export LD_LIBRARY_PATH={libs}${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}
    exec -a "$0" "{prog}" "$@"
    """
        ).format(libs=libs, prog=path)
    ).encode("utf8")


def update_bins(srcpath: str, dstpath: str):
    python = os.path.join(dstpath, "root", "bin", "python")
    shimdir = os.path.join(dstpath, "root", "shims")
    if os.path.isdir(shimdir):
        shutil.rmtree(shimdir)

    os.mkdir(shimdir)
    for name in os.listdir(os.path.join(srcpath, "root", "bin")):
        if os.path.isfile(os.path.join(dstpath, "root", "bin", name)):
            continue

        shimpath = os.path.join(dstpath, "root", "shims", name)
        path = os.path.join(srcpath, "root", "libexec", name)
        if not os.path.isfile(path):
            path = os.path.join(srcpath, "root", "bin", name)
        if not os.path.isfile(path):  # if folder, ignore
            continue

        with open(path, "rb") as f:
            text = f.read()
        with open(shimpath, "wb") as f:
            f.write(rewrite_executable(path, python, text))
        os.chmod(shimpath, 0o755)


def create_pth(config: dict, srcpath: str, dstpath: str):
    path = os.path.join(
        dstpath,
        "root",
        "lib",
        "python" + config["python-version"],
        "site-packages",
        "_komodo.pth",
    )
    with open(path, "w") as f:
        for lib in "lib64", "lib":
            f.write(
                os.path.join(
                    srcpath,
                    "root",
                    lib,
                    "python" + config["python-version"],
                    "site-packages",
                )
                + "\n"
            )


def parse_args(args: List[str]):
    if args is None:
        args = sys.argv[1:]

    ap = ArgumentParser()
    ap.add_argument(
        "--check",
        action="store_true",
        default=False,
        help="Check if this komodoenv can be updated",
    )

    return ap.parse_args(args)


def main(args: List[str] = None):
    args = parse_args(args)

    config = read_config()
    current = current_track(config)
    if not should_update(config, current):
        return

    check_same_distro(config)

    if args.check and not can_update(config):
        sys.exit(
            "Warning: Your komodoenv is out of date. You will need to recreate komodo"
        )

    elif args.check:
        sys.exit(
            dedent(
                """\
        Warning: Your komodoenv is out of date. To update to the latest komodo release ({rel}), run the following command:

        \tkomodoenv-update

        """.format(
                    rel=os.path.basename(current["current-release"])
                )
            )
        )

    config.update(current)
    write_config(config)

    srcpath = os.path.join(config["komodo-root"], config["current-release"])
    if not os.path.isdir(os.path.join(srcpath, "root")):
        srcpath += rhel_version_suffix()

    dstpath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    update_bins(srcpath, dstpath)
    update_enable_script(srcpath, dstpath)
    create_pth(config, srcpath, dstpath)


if __name__ == "__main__":
    main()
