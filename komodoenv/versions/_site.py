# -*- coding: utf-8 -*-
"""
A shim module to get komodoenv to behave. Based on virtualenv's site.py for
Python 2.
"""
import sys


def main():
    """Patch what needed, and invoke the original site.py"""
    config = read_pykenv()

    sys.executable = sys.executable.replace("libexec", "bin")
    sys.real_prefix = sys.base_prefix = config["base-prefix"]
    sys.base_exec_prefix = config["base-exec-prefix"]
    sys.base_executable = config["base-executable"]
    rewrite_standard_library_sys_path()
    disable_user_site_package()
    load_host_site(config["site-packages"])
    add_global_site_packages()


def load_host_site(site_packages):
    """Trigger reload of site.py"""
    # Upstream virtualenv does some smart things in order to work on Ubuntu
    # with its dist-packages, which we don't care to do.
    here = __file__

    if sys.version_info >= (3,4):
        from importlib import reload
    reload(sys.modules["site"])

    import os

    addsitedir = sys.modules["site"].addsitedir
    for path in site_packages.split(":"):
        sitepath = os.path.abspath(os.path.join(here, path))
        if sitepath not in sys.path:
            addsitedir(sitepath)


def read_pykenv():
    """read pykenv.cfg"""
    config_file = "{}/../komodoenv.conf".format(sys.prefix)
    with open(config_file) as f:
        lines = f.readlines()
    config = {}
    for line in lines:
        try:
            split_at = line.index("=")
        except ValueError:
            continue  # ignore bad/empty lines
        else:
            config[line[:split_at].strip()] = line[split_at + 1:].strip()
    return config


def rewrite_standard_library_sys_path():
    exe_dir = basedir(sys.executable)
    for at, path in enumerate(sys.path):
        # path = abspath(path)
        # Don't rewrite executable directory
        if path == exe_dir:
            continue
        sys.path[at] = map_path(path, exe_dir)

    # the rewrite above may have changed elements from PYTHONPATH, revert
    # these, but only if python wasn't started with -E "ignore environment"
    # flag
    if sys.flags.ignore_environment:
        return

    import os
    pythonpaths = set(os.environ.get("PYTHONPATH", "").split(os.pathsep))
    sys.path.extend(pythonpaths)


def abspath(relpath):
    parts = relpath.split("/")
    path = []
    at = len(parts) - 1
    while at >= 0:
        if parts[at] == "..":
            at -= 1
        else:
            path.append(parts[at])
        at -= 1
    return "/".join(path[::-1])


def map_path(path, exe_dir):
    if path_starts_with(path, exe_dir):
        orig_exe_dir = basedir(sys.base_executable)
        return orig_exe_dir + path[len(exe_dir):]
    elif path_starts_with(path, sys.prefix):
        return sys.base_prefix + path[len(sys.prefix):]
    elif path_starts_with(path, sys.exec_prefix):
        return sys.base_exec_prefix + path[len(sys.exec_prefix):]
    return path


def basedir(path):
    return path[:path.rfind("/")]


def path_starts_with(path, prefix):
    return path.startswith(prefix if prefix[-1] == "/" else prefix + "/")


def disable_user_site_package():
    """Flip the switch on enable user site package"""
    sys.original_flags = sys.flags

    class Flags(object):
        def __init__(self):
            self.__dict__ = { key: getattr(sys.flags, key) for key in dir(sys.flags) if not key[0] == "_" }

def add_global_site_packages():
    """add the global site-packages"""
    import site

    # add user site package
    sys.flags = sys.original_flags
    site.ENABLE_USER_SITE = None
    orig_prefixes = None
    try:
        orig_prefixes = site.PREFIXES
        site.PREFIXES = [sys.base_prefix, sys.base_exec_prefix]
        site.main()
    finally:
        site.PREFIXES = orig_prefixes


main()
