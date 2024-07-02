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


def test_track(tmpdir):
    with tmpdir.as_cwd():
        (tmpdir / "bleeding").mkdir()

        actual = update.current_track(
            {"komodo-root": str(tmpdir), "tracked-release": "bleeding"},
        )
        assert actual["tracked-release"] == "bleeding"
        assert actual["current-release"] == "bleeding"
        assert abs(float(actual["mtime-release"]) - time.time()) <= 1.0


def test_track_symlink(tmpdir):
    with tmpdir.as_cwd():
        (tmpdir / "bleeding").mkdir()
        (tmpdir / "stable").mksymlinkto("bleeding")

        actual = update.current_track(
            {"komodo-root": str(tmpdir), "tracked-release": "stable"},
        )
        assert actual["tracked-release"] == "stable"
        assert actual["current-release"] == "bleeding"
        assert (
            abs(float(actual["mtime-release"]) - time.time()) <= 1.0
        )  # This *could* cause false-negatives if for


def test_should_update_trivial(tmpdir):
    with tmpdir.as_cwd():
        (tmpdir / "bleeding").mkdir()

        config = update.current_track(
            {"komodo-root": str(tmpdir), "tracked-release": "bleeding"},
        )
        assert not update.should_update(config, config)


def test_should_update_time(tmpdir):
    with tmpdir.as_cwd():
        (tmpdir / "bleeding").mkdir()

        config = update.current_track(
            {"komodo-root": str(tmpdir), "tracked-release": "bleeding"},
        )

        (tmpdir / "bleeding").remove()
        time.sleep(0.01)
        (tmpdir / "bleeding").mkdir()

        current = update.current_track(
            {"komodo-root": str(tmpdir), "tracked-release": "bleeding"},
        )
        assert update.should_update(config, current)


def test_should_update_symlink(tmpdir):
    with tmpdir.as_cwd():
        (tmpdir / "a").mkdir()
        (tmpdir / "b").mkdir()
        (tmpdir / "stable").mksymlinkto("a")

        config = update.current_track(
            {"komodo-root": str(tmpdir), "tracked-release": "stable"},
        )

        (tmpdir / "stable").remove()
        (tmpdir / "stable").mksymlinkto("b")

        current = update.current_track(
            {"komodo-root": str(tmpdir), "tracked-release": "stable"},
        )
        assert update.should_update(config, current)


def test_get_pkg_version_exists():
    ver = update.get_pkg_version(
        {"python-version": "{}.{}".format(*sys.version_info)},
        (Path(sys.executable) / ".." / "..").resolve(),
        "pip",
    )

    assert ver == distribution("pip").version


def test_get_pkg_version_none():
    ver = update.get_pkg_version(
        {"python-version": "{}.{}".format(*sys.version_info)},
        (Path(sys.executable) / ".." / "..").resolve(),
        "this-package-doesnt-exist",
    )

    assert ver is None
