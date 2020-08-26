import os
import sys
import pytest
from six import ensure_binary
from subprocess import Popen, PIPE, check_output, CalledProcessError
from komodoenv.__main__ import main


ENABLE_BASH = """\
export KOMODO_RELEASE={name}

export _PRE_KOMODO_PATH="$PATH"
export PATH={root}/{name}/root/bin${{PATH:+:${{PATH}}}}

hash -r
"""


def _run(args, script):
    proc = Popen(args, stdin=PIPE)
    proc.communicate(ensure_binary(script))
    return proc.returncode


def bash(script):
    return _run(("/bin/bash", "-eux"), script)


def csh(script):
    return _run(("/bin/csh", "-f"), script)


def test_test_bash():
    """Sanity test for testing bash"""
    assert bash("echo hello\necho world") == 0
    assert bash("exit 1") == 1
    assert bash("echo $OH_NO_AN_UNBOUND_VARIABLE") == 1
    assert bash("/bin/false;exit 0") == 1


def test_test_csh():
    """Sanity test for testing csh"""
    assert csh("echo hello\necho world") == 0
    assert csh("exit 1") == 1
    assert csh("echo $OH_NO_AN_UNBOUND_VARIABLE") == 1


@pytest.fixture(scope="module")
def komodo_root(tmp_path_factory):
    """Here we mock a komodo environment.

    "Komodo environment? You mean a garbage dumb? Har har."
    """
    path = tmp_path_factory.mktemp("prog-res-komodo")

    symlinks = {
        "2030.01-py36": "2030.01.00-py36",
        "unstable-py36": "2030.01-py36",
        "testing-py36": "2030.01-py36",
        "stable-py36": "2030.01-py36",
        "2030.01-py27": "2030.01.00-py27",
        "unstable-py27": "2030.01.00-py27",
        "testing-py26": "2030.01.00-py27",
        "stable-py36": "2030.01.00-py27",
        "stable": "stable-py36",
    }

    # Install and configure python 2
    check_output(
        [
            sys.executable,
            "-m",
            "virtualenv",
            "-ppython2",
            str(path / "2030.01.00-py27/root"),
        ]
    )
    check_output(
        [str(path / "2030.01.00-py27/root/bin/pip"), "install", "numpy==1.16.6"]
    )

    # Install and configure python 3
    check_output(
        [
            sys.executable,
            "-m",
            "virtualenv",
            "-ppython3",
            str(path / "2030.01.00-py36/root"),
        ]
    )
    check_output(
        [str(path / "2030.01.00-py36/root/bin/pip"), "install", "numpy==1.18.4"]
    )

    # Install and configure python 3 again
    check_output(
        [
            sys.executable,
            "-m",
            "virtualenv",
            "-ppython3",
            str(path / "2030.01.01-py36/root"),
        ]
    )
    check_output(
        [str(path / "2030.01.01-py36/root/bin/pip"), "install", "numpy==1.19.1"]
    )

    for name in os.listdir(str(path)):
        (path / name / "enable").write_text(ENABLE_BASH.format(root=path, name=name))

    for src, dst in symlinks.items():
        (path / src).symlink_to(path / dst)

    return path


@pytest.fixture(scope="function")
def komodoenv_path(komodo_root, tmp_path_factory, request):
    marker = request.node.get_closest_marker("releases")
    if marker is None:
        releases = ["stable"]
    else:
        releases = marker.args

    main(map(str, ["--root", komodo_root, "--release", release, tmp_path]))
    return tmp_path


def test_init_bash(komodo_root, tmp_path):
    main(
        map(
            str,
            ["--root", komodo_root, "--release", "2030.01.00-py36", tmp_path / "kenv"],
        )
    )

    script = """\
    source {kmd}/enable

    [[ $(which python) == "{kmd}/root/bin/python" ]]
    [[ $(python -c "import numpy;print(numpy.__version__)") == "1.18.4" ]]
    """.format(
        kmd=tmp_path / "kenv"
    )

    assert bash(script) == 0


def test_init_csh(komodo_root, tmp_path):
    main(
        map(
            str,
            ["--root", komodo_root, "--release", "2030.01.00-py36", tmp_path / "kenv"],
        )
    )

    script = """\
    source {kmd}/enable.csh

    test `which python` = "{kmd}/root/bin/python" || exit 1
    test `python -c "import numpy;print(numpy.__version__)"` || exit 2
    """.format(
        kmd=tmp_path / "kenv"
    )

    assert csh(script) == 0


def test_update(request, komodo_root, tmp_path):
    main(
        map(
            str, ["--root", komodo_root, "--release", "2030.01-py36", tmp_path / "kenv"]
        )
    )

    # Verify that komodo hasn't been updated
    check_output([str(tmp_path / "kenv/root/bin/komodoenv-update"), "--check"])

    # Update to 2030.01.01
    (komodo_root / "2030.01-py36").unlink()
    (komodo_root / "2030.01-py36").symlink_to("2030.01.01-py36")

    def revert():
        (komodo_root / "2030.01-py36").unlink()
        (komodo_root / "2030.01-py36").symlink_to("2030.01.00-py36")

    request.addfinalizer(revert)

    # There's now an update
    with pytest.raises(CalledProcessError):
        check_output([str(tmp_path / "kenv/root/bin/komodoenv-update"), "--check"])

    # Update
    script = """\
    set +e
    source {kmd}/enable
    set -e

    komodoenv-update
    """.format(
        kmd=tmp_path / "kenv"
    )
    assert bash(script) == 0

    # Check that our numpy is updated
    script = """\
    source {kmd}/enable

    [[ $(which python) == "{kmd}/root/bin/python" ]]
    [[ $(python -c "import numpy;print(numpy.__version__)") == "1.19.1" ]]
    """.format(
        kmd=tmp_path / "kenv"
    )
    assert bash(script) == 0


def test_autodetect(komodo_root, tmp_path):
    script = """\
    # Source komodo release and autodetect
    source {root}/stable/enable
    {python} -m komodoenv --root={root} {kmd}

    # Test
    source {kmd}/enable
    [[ $(which python) == "{kmd}/root/bin/python"  ]]
    """.format(
        root=komodo_root, python=sys.executable, kmd=tmp_path / "kenv"
    )

    assert bash(script) == 0


def test_autodetect_fail(komodo_root, tmp_path):
    script = """\
    # Unset KOMODO_RELEASE in case it is set prior to pytest
    unset KOMODO_RELEASE
    {python} -m komodoenv --root={root} {kmd}
    """.format(
        root=komodo_root, python=sys.executable, kmd=tmp_path / "kenv"
    )

    assert bash(script) == 1
