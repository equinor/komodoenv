from __future__ import print_function
import os
import sys
import re
import argparse
import logging
import distro
import subprocess
from typing import Union, Tuple
from shutil import rmtree
from pathlib import Path
from komodoenv.creator import Creator
from komodoenv.statfs import is_nfs
from colors import red, yellow, strip_color


def get_release_maturity_text(release_path):
    """Returns a comment informing the user about the maturity of the release that
    they've chosen. Eg, warn users if they want bleeding, pat them on the back
     if they want stable, etc.

    """
    name = release_path.name

    if name.startswith("bleeding"):
        return yellow(
            "Warning: Tracking a bleeding release of komodo. It changes every day. "
            "You will need to recreate komodoenv in order to use new "
            "executables in komodo.\n"
        )
    elif name.startswith("unstable"):
        return yellow("Warning: Tracking an unstable release of komodo.\n")
    elif name.startswith("testing"):
        return yellow("Warning: Tracking a testing release of komodo.\n")
    elif name.startswith("stable"):
        return "Tracking a stable release of komodo.\n"
    else:
        return yellow(
            "Warning: Tracking an untracked release. It will not receive updates. "
            "This'll require recreating komodoenv to get updated software.\n"
        )


def distro_suffix():
    # Workaround to make tests pass on Github Actions
    if "GITHUB_ACTIONS" in os.environ:
        return "-rhel7"

    if distro.id() != "rhel":
        sys.exit("komodoenv only supports Red Hat Enterprise Linux")
    return f"-rhel{distro.major_version()}"


def resolve_release(root: Union[Path, str], name: str) -> Tuple[Path, Path]:
    """Autodetect komodo release heuristically"""
    if not (root / name / "enable").is_file():
        sys.exit(f"'{root / name}' is not a valid komodo release")

    lines = (
        subprocess.check_output(
            [
                "/bin/bash",
                "-c",
                f"source {root / name / 'enable'};which python;python --version",
            ]
        )
        .decode("utf-8")
        .splitlines(keepends=False)
    )

    assert len(lines) == 2
    actual_path = Path(lines[0]).parent.parent.parent  # <path>/root/bin/python
    major, minor = re.search(r"Python (\d).(\d+)", lines[1]).groups()
    pyver = "-py" + major + minor

    m = re.match("^(.*?)(?:-py[0-9]+)?(?:-rhel[0-9]+)?$", name)
    assert m is not None
    name = m[1] + pyver

    print(f"Looking for {name}")

    for mode in "stable", "testing", "unstable", "bleeding":
        for rhver in "", distro_suffix():
            dir_ = root / (mode + pyver + rhver)
            track = root / (mode + pyver)
            if not (dir_ / "root").is_dir():
                # stable-rhel7 isn't a thing. Try resolving and appending 'rhver'
                dir_ = (root / (mode + pyver)).resolve()
                dir_ = dir_.parent / (dir_.name + distro_suffix())
            if not (dir_ / "root").is_dir():
                continue
            symlink = dir_.resolve()
            if symlink.name == actual_path.name:
                return (symlink, track)

    sys.exit("Could not automatically detect Komodo release")


def parse_args(args):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="Overwrite exising komodoenv",
    )
    ap.add_argument(
        "-r",
        "--release",
        type=str,
        default=os.environ.get("KOMODO_RELEASE", "bleeding"),
        help="Komodo release to base komodoenv on. Defaults to currently active komodo release",
    )
    ap.add_argument(
        "-t",
        "--track",
        type=str,
        default=None,
        help="Komodo release on which to base updates",
    )
    ap.add_argument(
        "--root",
        type=str,
        default="/prog/res/komodo",
        help="Absolute path to komodo root (default: /prog/res/komodo)",
    )
    ap.add_argument(
        "--force-color", action="store_true", default=False, help="Force color output"
    )
    ap.add_argument("destination", type=str, help="Where to create komodoenv")

    args = ap.parse_args(args)

    args.root = Path(args.root)
    assert args.root.is_dir()

    if "/" in args.release:
        args.release = Path(args.release)
    elif isinstance(args.release, str):
        args.release = Path(args.root) / args.release

    if not args.release or not args.track:
        args.release, args.track = resolve_release(args.root, str(args.release))
    args.track = Path(args.track)
    args.destination = Path(args.destination).absolute()

    if args.release is None or not args.release.is_dir():
        logging.error(
            "Could not automatically detect active Komodo release. "
            "Either enable a Komodo release that supports komodoenv "
            "or specify release manually with the "
            "`--release' argument. "
        )
        ap.print_help()
        sys.exit(1)

    return args


def main(args=None):
    texts = {
        "beta": red(
            "Komodoenv is still in beta. Be aware that issues might occur and "
            "recreating environments once in a while is necessary.\n"
        ),
        "nfs": yellow(
            "Warning: Komodoenv target directory is not located on an NFS "
            "filesystem. Be aware that multi-machine workloads via eg. LFS "
            "might not work correctly.\n"
        ),
    }

    if args is None:
        args = sys.argv[1:]
    args = parse_args(args)

    if args.destination.is_dir() and args.force:
        rmtree(str(args.destination), ignore_errors=True)
    elif args.destination.is_dir():
        sys.exit("Destination directory already exists: {}".format(args.destination))
        sys.exit(1)

    use_color = args.force_color or (sys.stdout.isatty() and sys.stderr.isatty())
    release_text = get_release_maturity_text(args.track)
    if not use_color:
        texts = {key: strip_color(val) for key, val in texts.items()}
        release_text = strip_color(release_text)

    print(texts["beta"], file=sys.stderr)
    print(release_text, file=sys.stderr)

    if not is_nfs(args.destination):
        print(texts["nfs"], file=sys.stderr)

    creator = Creator(args.root, args.release, args.track, args.destination, use_color)
    creator.create()


if __name__ == "__main__":
    main()
