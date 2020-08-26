from __future__ import print_function
import os
import sys
import re
import argparse
import logging
from shutil import rmtree
from pathlib import Path
from komodoenv.update import rhel_version
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


def autodetect(root):
    """Autodetect komodo release heuristically"""
    name = os.environ.get("KOMODO_RELEASE", "")
    if not name:
        return None

    name = os.environ["KOMODO_RELEASE"]

    release_root = root / os.environ["KOMODO_RELEASE"]
    if not release_root.is_dir():
        return None

    match = re.search("(-py[0-9]+(?:-rhel[0-9]+)?)$", name)
    if not match:
        # Unrecognised suffix -- can't track concrete release
        return

    suffix = match[1]
    for mode in "stable", "testing", "unstable", "bleeding":
        dir_ = root / (mode + suffix)
        print(dir_)
        if not (dir_ / "root").is_dir():
            continue
        symlink = dir_.resolve()
        if symlink.name == name:
            return symlink

    return None


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
        required=False,
        help="Komodo release to base komodoenv on. Defaults to currently active komodo release",
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

    if args.release is None:
        args.release = autodetect(args.root)
    elif "/" in args.release:
        args.release = Path(args.release)
    else:
        args.release = args.root / args.release

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
    release_text = get_release_maturity_text(args.release)
    if not use_color:
        texts = {key: strip_color(val) for key, val in texts.items()}
        release_text = strip_color(release_text)

    print(texts["beta"], file=sys.stderr)
    print(release_text, file=sys.stderr)

    if not is_nfs(args.destination):
        print(texts["nfs"], file=sys.stderr)

    creator = Creator(args.root, args.release, args.destination, use_color)
    creator.create()


if __name__ == "__main__":
    main()
