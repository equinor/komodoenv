import pytest
from pathlib import Path
import komodoenv.__main__ as main


@pytest.mark.parametrize(
    "expect,track_name,name",
    [
        # Bleeding is py36, rhel7
        ("bleeding-py36-rhel7", "bleeding-py36", "bleeding"),
        ("bleeding-py36-rhel7", "bleeding-py36", "bleeding-py3"),
        ("bleeding-py36-rhel7", "bleeding-py36", "bleeding-py36"),
        # Stable is py36, unspecified rhel
        ("2030.01.00-py36", "stable-py36", "stable"),
        ("2030.01.00-py36", "stable-py36", "stable-py3"),
        ("2030.01.00-py36", "stable-py36", "stable-py36"),
        ("2030.01.00-py36", "stable-py36", "2030.01"),
        ("2030.01.00-py36", "stable-py36", "2030.01.00-py36"),
    ],
)
def test_resolve_simple(komodo_root, track_name, name, expect):
    release, tracked = main.resolve_release(komodo_root, name)
    assert release == komodo_root / expect
    assert tracked == komodo_root / track_name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "bleed",
        "bleeding-",
        # Unstable points to a non-existant, future version of RHEL and
        # therefore not possible to resolve
        "unstable",
        "unstable-py3",
        "unstable-py38",
        "2030.03.00-py38",
        "2030.03.00-py38-rhel9",
    ],
)
def test_resolve_fail(komodo_root, name):
    with pytest.raises(SystemExit):
        main.resolve_release(komodo_root, name)
