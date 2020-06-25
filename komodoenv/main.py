import sys
import os
import argparse
import re
import textwrap
from shutil import copy2 as copy
from pathlib import Path
from .release import Release
from .bundle import get_embed_wheels


KOMODO_ROOT = Path("/prog/res/komodo")


# Something that looks like a python with an optional version
PYTHON_PATTERN = re.compile("^python[0-9.]*$")


MODULE_TESTS = ("{}.so", "{}module.so", "{}.py", "{}.pyc", "{}")


def _required_modules(release):
    majver = release.majver
    minver = release.minver
    modules = ['os', 'posix', 'posixpath', 'genericpath',
               'fnmatch', 'locale', 'encodings', 'codecs',
               'stat', 'readline', 'copy_reg', 'types',
               're', 'sre', 'sre_parse', 'sre_constants', 'sre_compile',
               'zlib']

    # windows-only modules we ignore: ['nt', 'ntpath']

    if majver == 2:
        if minver >= 6:
            modules.extend(['warnings', 'linecache', '_abcoll', 'abc'])
        if minver >= 7:
            modules.extend(['_weakrefset'])
        modules.extend(["UserDict"])
    elif majver == 3:
        modules.extend([
            '_abcoll', 'warnings', 'linecache', 'abc', 'io', '_weakrefset',
    	    'copyreg', 'tempfile', 'random', '__future__', 'collections',
    	    'keyword', 'tarfile', 'shutil', 'struct', 'copy', 'tokenize',
    	    'token', 'functools', 'heapq', 'bisect', 'weakref', 'reprlib'
        ])
        if minver >= 2:
            modules[-1] = f"config-{majver}"
        if minver >= 3:
            modules.extend([
        	    'base64', '_dummy_thread', 'hashlib', 'hmac',
        	    'imp', 'importlib', 'rlcompleter'
            ])
        if minver >= 4:
            modules.extend([
                'operator',
                '_collections_abc',
                '_bootlocale',
            ])
        if minver >= 6:
            modules.extend(['enum'])
    return modules


def _required_files(release):
    majver = release.majver
    minver = release.minver
    files = ["lib-dynload", "config"]

    if majver == 3:
        if minver >= 2:
            files.append(f"config-{majver}")
        if minver >= 3:
            import sysconfig
            platdir = sysconfig.get_config_var('PLATDIR')
            files.append(platdir)

    return files


def _gen_shim(envroot: Path, relroot: Path, basename: str) -> str:
    libexec = envroot
    return """#!/bin/bash -eu
    export LD_LIBRARY_PATH={envroot}/lib:{relroot}/lib:{relroot}/lib64
    {libexec}/libexec/{basename} "$@"
    """.format(envroot=envroot, relroot=relroot, basename=basename, libexec=libexec)


def _create_shims(src: Path, dst: Path, subdir: str):
    relroot = src
    envroot = dst
    src /= subdir
    dst /= subdir

    dst.mkdir()
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)

        for file_ in files:
            if not PYTHON_PATTERN.match(file_):
                continue
            file__ = dst/rel/file_
            file__.touch(mode=0o755)
            file__.write_text(_gen_shim(envroot, relroot, file_))


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


def _install_wheels(release):
    SCRIPT = textwrap.dedent("""
        import sys
        import pkgutil
        import tempfile
        import os

        import pip

        # cert_data = pkgutil.get_data("pip._vendor.requests", "cacert.pem")
        # if cert_data is not None:
        #     cert_file = tempfile.NamedTemporaryFile(delete=False)
        #     cert_file.write(cert_data)
        #     cert_file.close()
        # else:
        #     cert_file = None

        try:
            args = ["install", "--ignore-installed"]
            # if cert_file is not None:
            #     args += ["--cert", cert_file.name]
            args += sys.argv[1:]

            sys.exit(pip.main(args))
        finally:
            pass
            # if cert_file is not None:
            #     os.remove(cert_file.name)
    """).encode("utf8")

    pythonpath = os.pathsep.join(map(str, get_embed_wheels(release)))
    env = {
        "PYTHONPATH": pythonpath,
        "PIP_USE_WHEEL": "1",
        "PIP_ONLY_BINARY": ":all:",
        "PIP_USER": "0",
        "PIP_NO_INDEX": "1"
    }
    print(release.run(SCRIPT, env=env, args=get_embed_wheels(release)))


def _create(root: Path, dest: Path):
    if dest.exists():
        print(f"Destination directory {dest} already exists. Please remove it.", file=sys.stderr)
        sys.exit(1)

    release = Release(root)
    root /= "root"

    # mkdir -p lib/python3.6/site-packages
    (dest/"lib"/release.libdir/"site-packages").mkdir(parents=True)

    # ln -s lib lib64
    (dest/"lib64").symlink_to(dest/"lib")

    for fn in _required_files(release):
        for libdir in "lib", "lib64":
            rel = Path(libdir)/release.libdir/fn
            if (root/rel).exists():
                (dest/rel).symlink_to(root/rel)

    for modname in _required_modules(release):
        if modname in release.builtin_module_names:
            continue

        found = False
        for fmt in MODULE_TESTS:
            for libdir in "lib", "lib64":
                test = Path(libdir)/release.libdir/fmt.format(modname)
                if (root/test).exists():
                    (dest/test).symlink_to(root/test)
                    found = True
        if not found:
            print(f"COULD NOT FIND {modname}")


    _create_shims(root, dest, "bin")
    _copy_pythons(root, dest)

    # Copy site.py
    src_site = Path(__file__).parent / "_site.py"
    dst_site = dest/"lib"/release.libdir/"site.py"
    copy(src_site, dst_site)

    orig_prefix = dest/"lib"/release.libdir/"orig-prefix.txt"
    orig_prefix.write_text(str(root))

    # Install pip, wheel, setuptools
    release._python_executable = dest/"bin"/"python"
    _install_wheels(release)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-r", "--release", default="stable-py36", type=str)
    ap.add_argument("dest", type=str)

    args = ap.parse_args()

    root = KOMODO_ROOT / args.release
    dest = Path(args.dest)
    _create(root, dest)
