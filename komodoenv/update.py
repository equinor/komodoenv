#!/usr/bin/python
"""
This is the update mechanism for komodo.

Note: This script must be kept compatible with Python 2.6 as long as RHEL6 is
alive and kicking. The reason for this is that we wish to use /usr/bin/python
to avoid any dependency on komodo during the update.
"""
import os
import shutil
from textwrap import dedent


KOMODO_ROOT = "/prog/res/komodo"


def read_config():
    with open(os.path.join(os.path.dirname(__file__), "komodoenv.conf")) as f:
        lines = f.readlines()
    config = {}
    for line in lines:
        try:
            split_at = line.index("=")
        except ValueError:
            continue
        else:
            key = line[:split_at].strip()
            val = line[split_at + 1:].strip()
            config[key] = val
    return config


def write_config(config):
    with open(os.path.join(os.path.dirname(__file__), "komodoenv.conf"), "w") as f:
        for key, val in config.items():
            f.write("{} = {}\n".format(key, val))


def current_track(tracked_release):
    rp = os.path.realpath(os.path.join(KOMODO_ROOT, tracked_release))
    st = os.stat(os.path.join(KOMODO_ROOT, tracked_release))

    config = {
        "tracked-release": tracked_release,
        "current-release": os.path.basename(rp),
        "mtime-release": st.st_mtime,
    }

    return config


def should_update(config):
    return config != current_track(config["tracked-release"])


def rewrite_executable(path, python, text):
    path = os.path.realpath(path)
    root = os.path.realpath(os.path.join(path, "..", ".."))
    libs = os.pathsep.join((os.path.join(root, "lib"), os.path.join(root, "lib64")))

    newline_pos = text.find(b"\n")
    if text[0:2] == b"#!" and b"python" in text[:newline_pos]:
        return "#!{python}\n{rest}".format(python=python, rest=text[newline_pos + 1:])

    return dedent(
        """\
    #!/bin/bash
    export LD_LIBRARY_PATH={libs}${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}
    {prog} "$@"
    """
    ).format(libs=libs, prog=path)


def update_bins(srcpath, dstpath):
    python = os.path.join(dstpath, "root", "bin", "python")
    shimdir = os.path.join(dstpath, "root", "shims")
    if os.path.isdir(shimdir):
        shutil.rmtree(shimdir)

    os.mkdir(shimdir)
    for name in os.listdir(os.path.join(srcpath, "root", "bin")):
        shimpath = os.path.join(dstpath, "root", "shims", name)
        path = os.path.join(srcpath, "root", "libexec", name)
        if not os.path.isfile(path):
            path = os.path.join(srcpath, "root", "bin", name)

        with open(path) as f:
            text = f.read()
        with open(shimpath, "w") as f:
            f.write(rewrite_executable(path, python, text))
        os.chmod(shimpath, 0o755)


def main():
    config = read_config()
    if not should_update(config):
        return
    config.update(current_track(config["tracked-release"]))
    write_config(config)

    srcpath = os.path.join(KOMODO_ROOT, config["current-release"])
    dstpath = os.path.join(os.path.dirname(__file__))
    update_bins(srcpath, dstpath)


if __name__ == "__main__":
    main()
