import sys
import os
import argparse
import re
import textwrap
import logging
from shutil import copy2 as copy
from pathlib import Path
from komodoenv.creator import create
from komodoenv.context import Context


KOMODO_ROOT = Path("/prog/res/komodo")


def autodetect():
    """Autodetect komodo release heuristically"""
    if "KOMODO_RELEASE" not in os.environ:
        return None

    release_root = KOMODO_ROOT / os.environ["KOMODO_RELEASE"]
    if not release_root.is_dir():
        return None

    for mode in "stable", "testing", "unstable", "bleeding":
        for suffix in "", "-py2", "-py27", "-py3", "-py36":
            name = mode + suffix
            dir_ = KOMODO_RELEASE / name
            if not dir_.is_dir() or not dir_.is_symlink():
                continue
            symlink = dir_.resolve()
            if symlink.name == name:
                return name

    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-r", "--release", type=str, required=False)
    ap.add_argument("dest", type=str)

    args = ap.parse_args()

    if args.release is None:
        args.release = autodetect()

    if args.release is None:
        logging.error(
            "Could not automatically detect active Komodo release. "
            "Either enable a Komodo release that supports komodoenv "
            "or specify release manually with the "
            "`--release' argument. "
        )
        ap.print_help()

    root = (KOMODO_ROOT / args.release).resolve()
    dest = Path(args.dest).absolute()

    ctx = Context(root, dest)
    print(ctx.type, ctx.version_info)

    create(ctx)
