import shutil
import sys
import time
from importlib.metadata import distribution
from pathlib import Path
from textwrap import dedent

from komodoenv import update


def test_rewrite_executable_python():
    pip = dedent(
        """\
    #!/usr/bin/python3
    # EASY-INSTALL-ENTRY-SCRIPT: 'pip==8.1.2','console_scripts','pip'
    __requires__ = 'pip==8.1.2'
    import sys
    from pkg_resources import load_entry_point

    if __name__ == '__main__':
        sys.exit(
            load_entry_point('pip==8.1.2', 'console_scripts', 'pip')()
        )""",
    )

    python = "/prog/res/komodo/bin/python"
    lines = pip.splitlines()
    lines[0] = "#!" + python

    actual = update.rewrite_executable(
        Path("/prog/res/komodo/bin/pip"),
        python,
        pip.encode("utf-8"),
    )
    assert "\n".join(lines).encode("utf-8") == actual


def test_rewrite_executable_binary():
    with open("/bin/sh", "rb") as f:
        sh = f.read()

    python = "unused"
    expect = dedent(
        """\
    #!/bin/bash
    export LD_LIBRARY_PATH=/prog/res/komodo/lib:/prog/res/komodo/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
    exec -a "$0" "/prog/res/komodo/bin/bash" "$@"
    """,
    )

    assert expect.encode("utf-8") == update.rewrite_executable(
        Path("/prog/res/komodo/bin/bash"),
        python,
        sh,
    )


def test_rewrite_executable_other_shebang():
    python = "unused"
    gem = dedent(
        """\
    #!/prog/res/komodo/bin/ruby
    puts :HelloWorld
        """,
    )

    expect = dedent(
        """\
    #!/bin/bash
    export LD_LIBRARY_PATH=/prog/res/komodo/lib:/prog/res/komodo/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
    exec -a "$0" "/prog/res/komodo/bin/gem" "$@"
    """,
    )

    assert expect.encode("utf-8") == update.rewrite_executable(
        Path("/prog/res/komodo/bin/gem"),
        python,
        gem.encode("utf-8"),
    )


def test_track(tmp_path):
    (tmp_path / "bleeding" / "root").mkdir(parents=True)

    actual = update.current_track(
        {"komodo-root": str(tmp_path), "tracked-release": "bleeding"},
    )
    assert actual["tracked-release"] == "bleeding"
    assert actual["current-release"] == "bleeding"
    assert abs(float(actual["mtime-release"]) - time.time()) <= 1.0


def test_track_symlink(tmp_path):
    (tmp_path / "bleeding" / "root").mkdir(parents=True)
    (tmp_path / "stable").symlink_to("bleeding")

    actual = update.current_track(
        {"komodo-root": str(tmp_path), "tracked-release": "stable"},
    )
    assert actual["tracked-release"] == "stable"
    assert actual["current-release"] == "bleeding"
    assert (
        abs(float(actual["mtime-release"]) - time.time()) <= 1.0
    )  # This *could* cause false-negatives if for


def test_should_update_trivial(tmp_path):
    (tmp_path / "bleeding" / "root").mkdir(parents=True)

    config = update.current_track(
        {"komodo-root": str(tmp_path), "tracked-release": "bleeding"},
    )
    assert not update.should_update(config, config)


def test_should_update_time(tmp_path):
    (tmp_path / "bleeding" / "root").mkdir(parents=True)

    config = update.current_track(
        {"komodo-root": str(tmp_path), "tracked-release": "bleeding"},
    )

    shutil.rmtree(tmp_path / "bleeding")
    time.sleep(0.01)
    (tmp_path / "bleeding" / "root").mkdir(parents=True)

    current = update.current_track(
        {"komodo-root": str(tmp_path), "tracked-release": "bleeding"},
    )
    assert update.should_update(config, current)


def test_should_update_symlink(tmp_path):
    (tmp_path / "a" / "root").mkdir(parents=True)
    (tmp_path / "b" / "root").mkdir(parents=True)
    (tmp_path / "stable").symlink_to("a")

    config = update.current_track(
        {"komodo-root": str(tmp_path), "tracked-release": "stable"},
    )

    (tmp_path / "stable").unlink()
    (tmp_path / "stable").symlink_to("b")

    current = update.current_track(
        {"komodo-root": str(tmp_path), "tracked-release": "stable"},
    )
    assert update.should_update(config, current)


def test_get_pkg_version_exists():
    ver = update.get_pkg_version(
        {"python-version": "{}.{}".format(*sys.version_info)},
        (Path(sys.executable).parents[1]),
        "pip",
    )
    assert ver == distribution("pip").version


def test_get_pkg_version_none():
    ver = update.get_pkg_version(
        {"python-version": "{}.{}".format(*sys.version_info)},
        (Path(sys.executable).parents[1]),
        "this-package-doesnt-exist",
    )

    assert ver is None
