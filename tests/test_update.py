import importlib
import shutil
import sys
import time
from importlib.metadata import distribution
from pathlib import Path
from textwrap import dedent
from unittest.mock import mock_open, patch

import pytest

from komodoenv import update

CONFIG_CONTENT = """
key1=value1
key2 = value2
# This is a comment
key3=value3
malformed_line
"""


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


def test_current_track_warning(tmp_path, capsys):
    sample_config = {
        "komodo-root": str(tmp_path),
        "tracked-release": "nonexistent_release",
    }
    with patch("komodoenv.update.rhel_version_suffix", return_value="-rhel8"):
        with pytest.raises(SystemExit) as sample:
            update.current_track(sample_config)

        expected_warning = f"Not able to find the tracked komodo release {sample_config['tracked-release']}. Will not update.\n"
        assert expected_warning in capsys.readouterr().err

        assert sample.value.code == 0


@pytest.mark.parametrize(
    "srcpath, package, validation",
    [
        (
            Path(sys.executable).parents[1],
            "pip",
            lambda x: x == distribution("pip").version,
        ),
        (
            Path("/nonexisting/path/here"),
            "pip",
            lambda x: x is None,
        ),
        (
            Path(sys.executable).parents[1],
            "this-package-doesnt-exist",
            lambda x: x is None,
        ),
    ],
)
def test_get_pkg_version(srcpath, package, validation):
    ver = update.get_pkg_version(
        {"python-version": "{}.{}".format(*sys.version_info)},
        srcpath,
        package,
    )
    assert validation(ver)


def test_read_config_with_valid_file():
    with patch(
        "komodoenv.update.open", new_callable=mock_open, read_data=CONFIG_CONTENT
    ):
        config = update.read_config("")
        assert config["key1"] == "value1"
        assert config["key2"] == "value2"
        assert config["key3"] == "value3"
        assert "malformed_line" not in config
        assert config["komodo-root"] == "/prog/res/komodo"


@pytest.mark.parametrize(
    "input_rhel_version, expected_rhel_version",
    [
        (
            "3.10.0-1062.el7.x86_64",
            "-rhel7",
        ),
        (
            "4.18.0-147.el8.x86_64",
            "-rhel8",
        ),
    ],
)
def test_rhel_version_suffix_with_distro_not_installed(
    input_rhel_version, expected_rhel_version
):
    with (
        patch.dict("sys.modules", {"distro": None}),
        patch(
            "platform.release",
            return_value=input_rhel_version,
        ),
    ):
        from komodoenv import update

        importlib.reload(update)
        assert update.rhel_version_suffix() == expected_rhel_version


def test_rhel_version_suffix_with_distro_not_installed_incompatible(capsys):
    with (
        patch.dict("sys.modules", {"distro": None}),
        patch("platform.release", return_value="5.6.14-300.fc32.x86_64"),
    ):
        from komodoenv import update

        importlib.reload(update)
        assert (
            "Warning: komodoenv is only compatible with RHEL7 or RHEL8"
            in capsys.readouterr().err
        )


@pytest.mark.parametrize(
    "original_rhel_version, current_rhel_version, warning_text, result",
    [
        (
            "rhel7",
            "3.10.0-1062.el7.x86_64",
            "",
            True,
        ),
        (
            "rhel7",
            "4.18.0-147.el8.x86_64",
            "Warning: Current distribution 'rhel8' doesn't",
            False,
        ),
    ],
)
def test_check_same_distro_true(
    capsys, original_rhel_version, current_rhel_version, warning_text, result
):
    config = {"linux-dist": original_rhel_version}
    with (
        patch.dict("sys.modules", {"distro": None}),
        patch("platform.release", return_value=current_rhel_version),
    ):
        from komodoenv import update

        importlib.reload(update)
        assert update.check_same_distro(config) == result
        assert warning_text in capsys.readouterr().err


@pytest.mark.parametrize(
    "old_version, new_version, result",
    [
        (
            "2.3.4",
            "2.5.1",
            True,
        ),
        (
            "2.3.4",
            "3.5.1",
            False,
        ),
        (
            "2.3.4",
            None,
            False,
        ),
    ],
)
def test_can_update(monkeypatch, old_version, new_version, result):
    monkeypatch.setattr("komodoenv.update.get_pkg_version", lambda _0, _1: new_version)
    monkeypatch.setattr(Path, "is_dir", lambda _: True)

    config = {
        "komodo-root": "/path/to/komodo",
        "tracked-release": "some-release",
        "komodoenv-version": old_version,
    }

    assert update.can_update(config) == result
