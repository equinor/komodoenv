import sys
import os
import argparse
import re
from shutil import copy2 as copy
from pathlib import Path


PYTHON_PATTERN = re.compile("^python[0-9.]*$")  # Something that looks like a
                                                # python with an optional
                                                # version
KOMODO_ROOT = Path("/prog/res/komodo")


def _gen_shim(envroot: Path, relroot: Path, basename: str) -> str:
    libexec = relroot
    if PYTHON_PATTERN.match(basename):
        libexec = envroot

    return """#!/bin/bash -eu
    export LD_LIBRARY_PATH={envroot}/lib:{relroot}/lib:{relroot}/lib64
    {libexec}/libexec/{basename} "$@"
    """.format(envroot=envroot, relroot=relroot, basename=basename, libexec=libexec)


def _symlink_recursively(src: Path, dst: Path, subdir: str):
    src /= subdir
    dst /= subdir

    dst.mkdir()
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)

        for dir_ in dirs:
            (dst/rel/dir_).mkdir()

        for file_ in files:
            (dst/rel/file_).symlink_to(src/rel/file_)


def _create_shims(src: Path, dst: Path, subdir: str):
    relroot = src
    envroot = dst
    src /= subdir
    dst /= subdir

    dst.mkdir()
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)

        for file_ in files:
            with open(dst/rel/file_, "w") as f:
                f.write(_gen_shim(envroot, relroot, file_))


def _copy_pythons(src: Path, dst: Path):
    src /= "libexec"
    dst /= "libexec"

    dst.mkdir()
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        for file_ in files:
            if not PYTHON_PATTERN.match(file_):
                continue
            copy(src/rel/file_, dst/rel/file_)


def _create(root: Path, dest: Path):
    if dest.exists():
        print(f"Destination directory {dest} already exists. Please remove it.", file=sys.stderr)
        sys.exit(1)

    dest.mkdir()
    for subdir in "lib", "lib64", "share":
        _symlink_recursively(root, dest, subdir)

    _create_shims(root, dest, "bin")
    _copy_pythons(root, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-r", "--release", default="stable-py36", type=str)
    ap.add_argument("dest", type=str)

    args = ap.parse_args()

    root = KOMODO_ROOT / args.release / "root"
    dest = Path(args.dest)
    _create(root, dest)
