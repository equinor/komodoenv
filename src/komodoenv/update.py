#!/usr/bin/python3
"""
This is the update mechanism for komodo.

Note: This script must be kept compatible with Python 3.6 as long as RHEL8 is
alive and kicking. The reason for this is that we wish to use /usr/bin/python3
to avoid any dependency on komodo during the update.
"""

import contextlib
import os
import platform
import re
import shutil
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from textwrap import dedent
from typing import Dict, List, Optional, Tuple

try:
    from distro import id as distro_id
    from distro import version_parts as distro_versions
except ImportError:
    # The 'distro' package isn't installed.
    #
    def distro_id() -> str:
        return "rhel"

    if ".el7" in platform.release():

        def distro_versions() -> Tuple[str, str, str]:
            return ("7", "0", "0")

    elif ".el8" in platform.release():

        def distro_versions() -> Tuple[str, str, str]:
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


def read_config() -> Dict[str, str]:
    with open(Path(__file__).parents[2] / "komodoenv.conf", encoding="utf-8") as f:
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


def check_same_distro(config: Dict[str, str]) -> bool:
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
        "recreate this komodoenv\n",
    )
    return False


def copy_config_dirs(config: Dict[str, str]) -> None:
    """
    Notebook 7 does not play well with komodoenv, and so we need to copy the
    data and config dirs from the komodo release.

    rips >= 2024.3.3.3 supports config file in venv/share/rips, so we sync it
    from komodo release.
    """
    srcpath = Path(config["komodo-root"]) / config["current-release"] / "root"
    if not srcpath.is_dir():
        srcpath = Path(str(srcpath.parent) + rhel_version_suffix()) / "root"
    dstpath = Path(__file__).resolve().parents[1]
    notebook_version = get_pkg_version(config, srcpath, "notebook")
    src_share_jupyter = srcpath / "share" / "jupyter"
    src_etc_jupyter = srcpath / "etc" / "jupyter"
    src_share_rips = srcpath / "share" / "rips"
    dst_share = dstpath / "share"
    dst_etc = dstpath / "etc"
    if (
        src_share_jupyter.is_dir()
        and src_etc_jupyter.is_dir()
        and (notebook_version and int(notebook_version[0]) >= 7)
    ):
        dst_etc.mkdir(exist_ok=True)
        dst_share.mkdir(exist_ok=True)
        try:
            subprocess.run(
                ["rsync", "-a", "--ignore-existing", src_share_jupyter, dst_share],
                check=True,
            )
            subprocess.run(
                ["rsync", "-a", "--ignore-existing", src_etc_jupyter, dst_etc],
                check=True,
            )
        except subprocess.CalledProcessError as err:
            print(f"An error occurred when fixing up jupyter environment: \n{err}")
            print("'Jupyter' may not work as intended in the komodoenv.")
    if src_share_rips.is_dir():
        dst_share.mkdir(exist_ok=True)
        try:
            subprocess.run(
                ["rsync", "-a", "--ignore-existing", src_share_rips, dst_share],
                check=True,
            )
        except subprocess.CalledProcessError as err:
            print(f"An error occurred when fixing up rips config: \n{err}")
            print("'rips' may not work as intended in the komodoenv.")


def get_pkg_version(
    config: Dict[str, str],
    srcpath: Path,
    package: str = "komodoenv",
) -> Optional[str]:
    """Locate `package`'s version in the current komodo distribution. This format is
    defined in PEP 376 "Database of Installed Python Distributions".

    Returns None if package wasn't found.
    """
    pkgdir = srcpath / "lib" / ("python" + config["python-version"]) / "site-packages"
    pattern = re.compile(f"^{package}-(.+).dist-info")

    if not pkgdir.is_dir():
        return None
    matches = []
    for entry in pkgdir.iterdir():
        match = pattern.match(entry.name)
        if match is not None:
            matches.append(match[1])
    if len(matches) > 0:
        return max(matches)
    return None


def can_update(config: Dict[str, str]) -> bool:
    """Compares the version of komodoenv that built the release with the one in the
    one we want to update to. If the major versions are the same, we know the
    layout is identical, and can be safely updated with this script.
    """
    track_path = (Path(config["komodo-root"]) / config["tracked-release"]).resolve()
    track_path = get_tracked_release(track_path)
    version = get_pkg_version(config, track_path / "root")
    if "komodoenv-version" not in config or version is None:
        return False

    current_maj = int(config["komodoenv-version"].split(".")[0])
    updated_maj = int(version.split(".")[0])

    return current_maj == updated_maj


def write_config(config: Dict[str, str]):
    with open(Path(__file__).parents[2] / "komodoenv.conf", "w", encoding="utf-8") as f:
        f.writelines(f"{key} = {val}\n" for key, val in config.items())


def get_tracked_release(
    tracked_release: Path, rhel_suffix: Optional[str] = None
) -> Path:
    if not rhel_suffix:
        rhel_suffix = rhel_version_suffix()

    custom_coordinate = find_custom_coordinate(tracked_release)
    detected_python_version = ""
    parts = Path(tracked_release).name.split("-")
    abs_path = Path(tracked_release).parent
    base_release = f"{abs_path}/{parts[0]}"
    for p in parts:
        if re.match(r"^(?:\d{8}|\d{4})$", p):
            base_release += f"-{p}"
        elif p.startswith("py"):
            detected_python_version = f"-{p}"

    for rp in [
        f"{base_release}{detected_python_version}{rhel_suffix}{custom_coordinate}",
        f"{base_release}{detected_python_version}{rhel_suffix}",
        f"{base_release}{detected_python_version}{custom_coordinate}",
        f"{base_release}{detected_python_version}",
    ]:
        possible_root_release = Path(rp).resolve()
        if (possible_root_release / "root").is_dir():
            return possible_root_release

    return Path()


def find_custom_coordinate(release_path: Path) -> str:
    if (release_path / "enable").is_file():
        with open(release_path / "enable", "r") as file:
            for line in file:
                if "CUSTOM_COORDINATE=" in line:
                    custom_coordinate_value = (
                        line.strip()
                        .split("CUSTOM_COORDINATE=")[1]
                        .strip('"')
                        .strip("-")
                    )
                    return "-" + custom_coordinate_value

    parts = release_path.name.split("-")
    possible_custom_coordinate = parts[-1]
    if len(parts) > 1 and not any(
        possible_custom_coordinate.startswith(token) for token in ("py", "rhel")
    ):
        return f"-{possible_custom_coordinate}"
    return ""


def current_track(config: Dict[str, str]) -> Dict[str, str]:
    path = Path(config["komodo-root"]) / config["tracked-release"]

    tracked_release = get_tracked_release(path.resolve())
    if not (tracked_release / "root").is_dir():
        print(
            f"Not able to find the tracked komodo release {config['tracked-release']}. Will not update.",
            file=sys.stderr,
        )
        sys.exit(0)
    st = path.stat()

    return {
        "tracked-release": config["tracked-release"],
        "current-release": tracked_release.name,
        "mtime-release": str(st.st_mtime),
    }


def should_update(config: Dict[str, str], current: Dict[str, str]) -> bool:
    return any(
        config[x] != current[x]
        for x in ("tracked-release", "current-release", "mtime-release")
    )


def enable_script(fmt: str, komodo_prefix: Path, komodoenv_prefix: Path) -> str:
    return fmt.format(
        komodo_prefix=str(komodo_prefix),
        komodo_release=komodo_prefix.name,
        komodoenv_prefix=str(komodoenv_prefix),
        komodoenv_release=komodoenv_prefix.name,
    )


def update_enable_script(komodo_prefix: Path, komodoenv_prefix: Path) -> None:
    with open(komodoenv_prefix / "enable", "w", encoding="utf-8") as f:
        f.write(enable_script(ENABLE_BASH, komodo_prefix, komodoenv_prefix))
    with open(komodoenv_prefix / "enable.csh", "w", encoding="utf-8") as f:
        f.write(enable_script(ENABLE_CSH, komodo_prefix, komodoenv_prefix))


def rewrite_executable(path: Path, python: str, text: bytes) -> bytes:
    path = path.resolve()
    root = path.parents[1]
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
    """,
        )
    ).encode("utf8")


def update_bins(srcpath: Path, dstpath: Path) -> None:
    python = dstpath / "root" / "bin" / "python"
    shimdir = dstpath / "root" / "shims"
    if shimdir.is_dir():
        shutil.rmtree(shimdir)

    shimdir.mkdir()
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
        shimpath.chmod(0o755)


def create_pth(config: Dict[str, str], srcpath: Path, dstpath: Path) -> None:
    path = (
        dstpath
        / "root"
        / "lib"
        / ("python" + config["python-version"])
        / "site-packages"
    )
    # If upgrading from an old komodoenv using '_komodo.pth'
    # to a newer which uses 'zzz_komodo.pth' we must make sure to
    # remove the old _komodo.pth.
    with contextlib.suppress(FileNotFoundError):
        (path / "_komodo.pth").unlink()

    python_paths = [
        f"{srcpath}/root/{lib}/python{config['python-version']}/site-packages"
        for lib in ("lib64", "lib")
    ]

    with open(path / "zzz_komodo_finder.py", "w", encoding="utf-8") as f:
        f.write(
            dedent(
                f"""\
                import sys
                from importlib.machinery import PathFinder

                KOMODO_PATHS = {python_paths!r}

                class KomodoFallbackFinder:
                    @classmethod
                    def find_spec(cls, fullname, path=None, target=None):
                        spec = PathFinder.find_spec(fullname, KOMODO_PATHS)
                        if spec:
                            return spec
                        return None

                def install():
                    if not any(isinstance(f, KomodoFallbackFinder) for f in sys.meta_path):
                        sys.meta_path.append(KomodoFallbackFinder())
                """
            )
        )
    # We use zzz_komodo.pth to try and make it the last .pth file to be processed
    # alphabetically, and thus allowing for other editable installs to 'overwrite'
    # komodo packages.
    with open(path / "zzz_komodo.pth", "w", encoding="utf-8") as f:
        f.write("import zzz_komodo_finder; zzz_komodo_finder.install()")


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


def main(args: Optional[List[str]] = None) -> None:
    args = parse_args(args)

    config = read_config()
    if not check_same_distro(config):
        return

    copy_config_dirs(config)

    current = current_track(config)
    if not should_update(config, current):
        return

    if args.check and not can_update(config):
        print(
            "Warning: Your komodoenv is out of date. You will need to recreate komodo",
            file=sys.stderr,
        )
        sys.exit(0)

    elif args.check:
        print(
            dedent(
                f"""\
        Warning: Your komodoenv is out of date. To update to the latest komodo release ({Path(current["current-release"]).name}), run the following command:

        \tkomodoenv-update

        """,
            ),
            file=sys.stderr,
        )
        sys.exit(0)

    config.update(current)
    write_config(config)

    srcpath = Path(config["komodo-root"]) / config["current-release"]

    dstpath = Path(__file__).resolve().parents[2]  # komodoenv/root/bin/update.py
    update_bins(srcpath, dstpath)
    update_enable_script(srcpath, dstpath)
    create_pth(config, srcpath, dstpath)
    # we run copy_config_dirs before and after updating to make sure it is always up to date
    copy_config_dirs(config)


if __name__ == "__main__":
    main()
