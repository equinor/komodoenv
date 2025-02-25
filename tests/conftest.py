import itertools
import os
import platform
import re
import shutil
from pathlib import Path
from subprocess import check_output

import pytest

KOMODO_TIMESTAMP = "-20250225-1209"


def rhel_version():
    return "7" if ".el7" in platform.release() else "8"


@pytest.fixture(scope="session")
def python311_path():
    """Locate Python 3.11 executable"""
    for exe in "/usr/bin/python3.11", str(shutil.which("python3.11")):
        if Path(exe).is_file():
            return exe
    msg = "Could not locate python3.11"
    raise RuntimeError(msg)


@pytest.fixture(scope="session")
def komodo_root(tmp_path_factory, python311_path):
    """Komodo mock environment"""
    # It takes forever to generate the virtualenvs. Let the developer set this
    # environment variable to reuse a previously-bootstrapped komodo root.
    if "KOMODOENV_TEST_REUSE" in os.environ:
        return Path(os.environ["KOMODOENV_TEST_REUSE"])

    path = tmp_path_factory.mktemp("prog-res-komodo")

    # Install and configure pythons
    _install(python311_path, path / "2030.01.00-py311", ["numpy==1.25.2"])
    _install(python311_path, path / "2030.01.01-py311", ["numpy==1.26.4"])
    _install(python311_path, path / "2030.02.00-py311")
    _install(python311_path, path / "2030.03.00-py311-rhel9")
    _install(
        python311_path,
        path / f"bleeding{KOMODO_TIMESTAMP}-py311-rhel{rhel_version()}-numpy1",
    )
    _install(python311_path, path / f"2025.04.01-py311-rhel{rhel_version()}-numpy1")

    for chain in (
        ("2030.01", "2030.01-py3", "2030.01-py311", "2030.01.00-py311"),
        ("2030.02", "2030.02-py3", "2030.02-py311", "2030.02.00-py311"),
        ("2030.03", "2030.03-py3", "2030.03-py311", "2030.03.00-py311"),
        ("2025.04", "2025.04-py3", "2025.04-py311", "2025.04.01-py311"),
        # Stable points to py311, unspecified-rhel
        ("stable", "stable-py3", "stable-py311", "2030.01-py311"),
        # Testing points to py311, rhel8, numpy1
        ("testing", "testing-py3", "testing-py311", "2025.04-py311"),
        # Bleeding points to py311, rhel8
        (
            "bleeding",
            "bleeding-py3",
            "bleeding-py311",
            f"bleeding{KOMODO_TIMESTAMP}-py311",
        ),
    ):
        for src, dst in itertools.pairwise(chain):
            (path / src).symlink_to(dst)

    return path


def _install(python: str, path: Path, packages=None):
    # Create virtualenv
    check_output(
        [
            python,
            "-m",
            "venv",
            str(path / "root"),
        ],
    )

    # Create enable scripts
    (path / "enable").write_text(
        f"export KOMODO_RELEASE={path.name}\nexport PATH={path}/root/bin:$PATH\n",
    )
    (path / "enable.csh").write_text(
        f"setenv KOMODO_RELEASE {path.name}\nsetenv PATH {path}/root/bin:$PATH\n",
    )

    # Create a redirect script if path contains '-rhelX'
    match = re.match("^(.+)-rhel[0-9]", path.name)

    optional_custom_coordinate = path.name.split("-")[-1]
    custom_coordinate = ""
    if optional_custom_coordinate and not any(
        optional_custom_coordinate.startswith(substring) for substring in ["py", "rhel"]
    ):
        custom_coordinate = "-" + optional_custom_coordinate

    if match is not None:
        p = path.parent / match[1]
        p.mkdir()
        (p / "enable").write_text(
            f'CUSTOM_COORDINATE="{custom_coordinate}"\nsource {path}/enable'
        )
        (p / "enable.csh").write_text(
            f'set CUSTOM_COORDINATE="{custom_coordinate}"\nsource {path}/enable.csh'
        )

    # Install additional packages
    if packages:
        check_output([str(path / "root/bin/pip"), "install", *packages])
