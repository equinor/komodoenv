#!/usr/bin/python3
"""
This is the update mechanism for komodo.

Note: This script must be kept compatible with Python 3.6 as long as RHEL7 is
alive and kicking. The reason for this is that we wish to use /usr/bin/python3
to avoid any dependency on komodo during the update.
"""

import os
import platform
import re
import shutil
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from textwrap import dedent
from typing import List

try:
    from distro import id as distro_id
    from distro import version_parts as distro_versions
except ImportError:
    # The 'distro' package isn't installed.
    #
    def distro_id():
        return "rhel"

    if "el7" in platform.release():

        def distro_versions():
            return ("7", "0", "0")

    elif "el8" in platform.release():

        def distro_versions():
            return ("8", "0", "0")

    else:
        sys.stderr.write("Warning: komodoenv is only compatible with RHEL7 or RHEL8")


ENABLE_BASH = """\
disable_komodo () {{
    if [[ -v _PRE_KOMODO_PATH ]]; then
        export PATH="${{_PRE_KOMODO_PATH}}"
        unset _PRE_KOMODO_PATH
    fi
    if [[ -v _PRE_KOMODO_MANPATH ]]; then
        export MANPATH="${{_PRE_KOMODO_MANPATH}}"
        unset _PRE_KOMODO_MANPATH
    fi
    if [[ -v _PRE_KOMODO_LD_LIBRARY_PATH ]]; then
        export LD_LIBRARY_PATH="${{_PRE_KOMODO_LD_LIBRARY_PATH}}"
        unset _PRE_KOMODO_LD_LIBRARY_PATH
    fi
    if [[ -v _PRE_KOMODO_PS1 ]]; then
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
export LD_LIBRARY_PATH={komodo_prefix}/root/lib:{komodo_prefix}/root/lib64${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}

export _PRE_KOMODO_PS1="${{PS1:-}}"
export PS1="({komodoenv_release} + {komodo_release}) ${{PS1:-}}"

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
        Path(__file__).parent / ".." / ".." / "komodoenv.conf", encoding="utf-8"
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
        config["komodo-root"] = (
            "prog/komodo" if Path("/prog/komodo").is_dir() else "/prog/res/komodo"
        )

    return config


def rhel_version_suffix() -> str:
    """
    Return the current running RHEL version as "-rhelX" where X is the major
    version. "" if not on RHEL.
    """

    return "-" + distro_id() + distro_versions()[0]


def check_same_distro(config: dict) -> bool:
    """Python might not run properly on a different distro than the one that
    komodoenv was first generated for. Returns True if the distro in the config
    matches ours, False otherwise.

    """
    confdist = config.get("linux-dist", "")
    thisdist = distro_id() + distro_versions()[0]
    if confdist == thisdist:
        return True

    sys.stderr.write(
        f"Warning: Current distribution '{thisdist}' doesn't match the one that "
        f"was used to generate this environment '{confdist}'. You might need to "
        "recreate this komodoenv\n"
    )
    return False


def copy_jupyter_dirs(config: dict) -> None:
    """
    Notebook 7 does not play well with komodoenv, and so we need to copy the
    data and config dirs from the komodo release.
    """
    srcpath = Path(config["komodo-root"]) / config["current-release"] / "root"
    if not srcpath.is_dir():
        srcpath = Path(str(srcpath) + rhel_version_suffix()) / "root"
    dstpath = Path(__file__).resolve().parents[1]
    notebook_version = get_pkg_version(config, srcpath, "notebook")
    if not (notebook_version and int(notebook_version[0]) >= 7):
        return
    src_share = srcpath / "share" / "jupyter"
    src_etc = srcpath / "etc" / "jupyter"
    dst_share = dstpath / "share"
    dst_etc = dstpath / "etc"
    if not (src_share.is_dir() or src_etc.is_dir()):
        return
    dst_etc.mkdir(exist_ok=True)
    dst_share.mkdir(exist_ok=True)
    try:
        subprocess.run(
            ["rsync", "-a", "--ignore-existing", src_share, dst_share], check=True
        )
        subprocess.run(
            ["rsync", "-a", "--ignore-existing", src_etc, dst_etc], check=True
        )
    except subprocess.CalledProcessError as err:
        print(f"An error occurred when fixing up jupyter environment: \n{err}")
        print("Jupyter may not work as intended in the komodoenv.")


def get_pkg_version(
    config: dict, srcpath: Path, package: str = "komodoenv"
) -> List[str]:
    """Locate `package`'s version in the current komodo distribution. This format is
    defined in PEP 376 "Database of Installed Python Distributions".

    Returns None if package wasn't found.
    """
    pkgdir = srcpath / "lib" / ("python" + config["python-version"]) / "site-packages"
    pattern = re.compile(f"^{package}-(.+).dist-info")

    matches = []
    for entry in pkgdir.iterdir():
        match = pattern.match(entry.name)
        if match is not None:
            matches.append(match[1])
    if len(matches) > 0:
        return max(matches)


def can_update(config: dict) -> bool:
    """Compares the version of komodoenv that built the release with the one in the
    one we want to update to. If the major versions are the same, we know the
    layout is identical, and can be safely updated with this script.

    """
    srcpath = (Path(config["komodo-root"]) / config["tracked-release"]).resolve()
    if not (srcpath / "root").is_dir():
        srcpath = Path(str(srcpath) + rhel_version_suffix())
    version = get_pkg_version(config, srcpath / "root")
    if "komodoenv-version" not in config or version is None:
        return False

    current_maj = int(config["komodoenv-version"].split(".")[0])
    updated_maj = int(version.split(".")[0])

    return current_maj == updated_maj


def write_config(config: dict):
    with open(
        Path(__file__).parent / ".." / ".." / "komodoenv.conf", "w", encoding="utf-8"
    ) as f:
        for key, val in config.items():
            f.write(f"{key} = {val}\n")


def current_track(config: dict) -> dict:
    path = Path(config["komodo-root"]) / config["tracked-release"]

    rp = path.resolve()
    st = path.stat()

    config = {
        "tracked-release": config["tracked-release"],
        "current-release": rp.name,
        "mtime-release": str(st.st_mtime),
    }

    return config


def should_update(config: dict, current: dict) -> bool:
    return any(
        config[x] != current[x]
        for x in ("tracked-release", "current-release", "mtime-release")
    )


def enable_script(fmt: str, komodo_prefix: Path, komodoenv_prefix: Path):
    return fmt.format(
        komodo_prefix=str(komodo_prefix),
        komodo_release=komodo_prefix.name,
        komodoenv_prefix=str(komodoenv_prefix),
        komodoenv_release=komodoenv_prefix.name,
    )


def update_enable_script(komodo_prefix: Path, komodoenv_prefix: Path):
    with open(komodoenv_prefix / "enable", "w", encoding="utf-8") as f:
        f.write(enable_script(ENABLE_BASH, komodo_prefix, komodoenv_prefix))
    with open(komodoenv_prefix / "enable.csh", "w", encoding="utf-8") as f:
        f.write(enable_script(ENABLE_CSH, komodo_prefix, komodoenv_prefix))


def rewrite_executable(path: Path, python: str, text: bytes):
    path = path.resolve()
    root = (path / ".." / "..").resolve()
    libs = os.pathsep.join([str(root / "lib"), str(root / "lib64")])

    newline_pos = text.find(b"\n")
    if (
        text[:2] == b"#!"
        and newline_pos >= 0
        and text[:newline_pos].find(b"python") >= 0
    ):
        return b"#!" + python.encode("utf8") + text[newline_pos:]

    return (
        dedent(
            f"""\
    #!/bin/bash
    export LD_LIBRARY_PATH={libs}${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}
    exec -a "$0" "{path!s}" "$@"
    """
        )
    ).encode("utf8")


def update_bins(srcpath: Path, dstpath: Path):
    python = dstpath / "root" / "bin" / "python"
    shimdir = dstpath / "root" / "shims"
    if shimdir.is_dir():
        shutil.rmtree(shimdir)

    os.mkdir(shimdir)
    for entry in (srcpath / "root" / "bin").iterdir():
        if (dstpath / "root" / "bin" / entry.name).is_file():
            continue

        shimpath = dstpath / "root" / "shims" / entry.name
        path = srcpath / "root" / "libexec" / entry.name
        if not path.is_file():
            path = srcpath / "root" / "bin" / entry.name
        if not path.is_file():  # if folder, ignore
            continue

        with open(path, "rb") as f:
            text = f.read()
        with open(shimpath, "wb") as f:
            f.write(rewrite_executable(path, str(python), text))
        os.chmod(shimpath, 0o755)


def create_pth(config: dict, srcpath: Path, dstpath: Path):
    path = (
        dstpath
        / "root"
        / "lib"
        / ("python" + config["python-version"])
        / "site-packages"
        / "_komodo.pth"
    )
    with open(path, "w", encoding="utf-8") as f:
        for lib in "lib64", "lib":
            f.write(
                str(
                    srcpath
                    / "root"
                    / lib
                    / ("python" + config["python-version"])
                    / "site-packages"
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

    if not check_same_distro(config):
        return

    copy_jupyter_dirs(config)

    current = current_track(config)

    if not should_update(config, current):
        return

    if args.check and not can_update(config):
        sys.exit(
            "Warning: Your komodoenv is out of date. You will need to recreate komodo"
        )

    elif args.check:
        sys.exit(
            dedent(
                f"""\
        Warning: Your komodoenv is out of date. To update to the latest komodo release ({Path(current["current-release"]).name}), run the following command:

        \tkomodoenv-update

        """
            )
        )

    config.update(current)
    write_config(config)

    srcpath = Path(config["komodo-root"]) / config["current-release"]
    if not (srcpath / "root").is_dir():
        srcpath = Path(str(srcpath) + rhel_version_suffix())

    dstpath = (Path(__file__).parent / ".." / "..").resolve()
    update_bins(srcpath, dstpath)
    update_enable_script(srcpath, dstpath)
    create_pth(config, srcpath, dstpath)
    # we run copy_jupyter_dirs before and after updating to make sure it is always run
    copy_jupyter_dirs(config)


if __name__ == "__main__":
    main()
