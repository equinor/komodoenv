import os
import re
import pytest
from typing import List, Optional
from pathlib import Path
from textwrap import dedent
from subprocess import Popen, PIPE, check_output, CalledProcessError


@pytest.fixture(scope="session")
def python36_path():
    """Locate Python 3.6 executable

    RHEL7/8      : yum install python3-dev
    Ubuntu 18.04 : apt-get install python3-{dev,venv}
    """
    exe = "/usr/bin/python3.6"
    if not os.path.isfile(exe):
        raise RuntimeError("Could not locate python3.6")
    return exe


@pytest.fixture(scope="session")
def python38_path():
    """Locate Python 3.8 executable

    On RHEL 7 python3.8 is found in SCL, but on RHEL 8 and Ubuntu (used by
    Github Actions) has it installed in the system.

    RHEL7        : yum install rh-python38-devel
    RHEL8        : yum install python38-devel
    Ubuntu 18.04 : apt-get install python3-venv python3.8-{dev,venv}
    """
    for exe in "/usr/bin/python3.8", "/opt/rh/rh-python38/root/bin/python3.8":
        if os.path.isfile(exe):
            return exe
    else:
        raise RuntimeError("Could not locate python3.8")


@pytest.fixture(scope="session")
def komodo_root(tmp_path_factory, python36_path, python38_path):
    """Komodo mock environment"""
    # It takes forever to generate the virtualenvs. Let the developer set this
    # environment variable to reuse a previously-bootstrapped komodo root.
    if "KOMODOENV_TEST_REUSE" in os.environ:
        return Path(os.environ["KOMODOENV_TEST_REUSE"])

    path = tmp_path_factory.mktemp("prog-res-komodo")

    # Install and configure pythons
    _install(python36_path, path / "2030.01.00-py36", ["numpy==1.18.4"])
    _install(python36_path, path / "2030.01.01-py36", ["numpy==1.19.1"])
    _install(python38_path, path / "2030.02.00-py38")
    _install(python38_path, path / "2030.03.00-py38-rhel9")
    _install(python36_path, path / "bleeding-py36-rhel7")

    for chain in (
        ("2030.01", "2030.01-py3", "2030.01-py36", "2030.01.00-py36"),
        ("2030.02", "2030.02-py3", "2030.02-py38", "2030.02.00-py38"),
        ("2030.03", "2030.03-py3", "2030.03-py38", "2030.03.00-py38"),
        # Stable points to py36, unspecified-rhel
        ("stable", "stable-py3", "stable-py36", "2030.01-py36"),
        # Testing points to py36, rhel7
        ("testing", "testing-py3", "testing-py36", "2030.02-py36"),
        # Unstable refers to a future version of RHEL
        ("unstable", "unstable-py3", "unstable-py38", "2030.03-py38"),
        # Bleeding points to py36, rhel7
        ("bleeding", "bleeding-py3", "bleeding-py36"),
    ):
        for src, dst in zip(chain[:-1], chain[1:]):
            (path / src).symlink_to(dst)

    return path


def _install(python: str, path: Path, packages: Optional[List[str]] = None):
    # Create virtualenv
    check_output(
        [
            python,
            "-m",
            "venv",
            str(path / "root"),
        ]
    )

    # Create enable scripts
    (path / "enable").write_text(
        f"export KOMODO_RELEASE={path.name}\nexport PATH={path}/root/bin:$PATH\n"
    )
    (path / "enable.csh").write_text(
        f"setenv KOMODO_RELEASE {path.name}\nsetenv PATH {path}/root/bin:$PATH\n"
    )

    # Create a redirect script if path ends in '-rhelX'
    match = re.match("^(.+)-rhel[0-9]+$", path.name)
    if match is not None:
        p = path.parent / match[1]
        p.mkdir()
        (p / "enable").write_text(f"source {path}/enable")
        (p / "enable.csh").write_text(f"source {path}/enable.csh")

    # Install additional packages
    if packages:
        check_output([str(path / "root/bin/pip"), "install"] + packages)
