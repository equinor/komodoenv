import pytest

import komodoenv.__main__ as main
from tests.conftest import rhel_version


def generate_test_params_simple(rhel_version):
    base_params = [
        ("2030.01.00-py38", "stable-py38", "stable"),
        ("2030.01.00-py38", "stable-py38", "stable-py3"),
        ("2030.01.00-py38", "stable-py38", "stable-py38"),
        ("2030.01.00-py38", "stable-py38", "2030.01"),
        ("2030.01.00-py38", "stable-py38", "2030.01.00-py38"),
        (f"bleeding-py38-rhel{rhel_version}", "bleeding-py38", "bleeding"),
        (f"bleeding-py38-rhel{rhel_version}", "bleeding-py38", "bleeding-py3"),
        (f"bleeding-py38-rhel{rhel_version}", "bleeding-py38", "bleeding-py38"),
    ]
    return base_params


@pytest.mark.parametrize(
    "expect, track_name,name",
    generate_test_params_simple(rhel_version()),
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
        # Singular release
        "2030.01.01-py38",
    ],
)
def test_resolve_fail(komodo_root, name):
    with pytest.raises(SystemExit):
        main.resolve_release(komodo_root, name)


def test_resolve_fail_singular(komodo_root):
    """
    When making a komodoenv of a singular release without --no-update, inform
    the user and exit.
    """
    with pytest.raises(SystemExit) as exc:
        main.resolve_release(komodo_root, "2030.01.01-py38")
    assert "--no-update" in str(exc.value)


def generate_test_params_no_update(rhel_version):
    base_params = [
        ("2030.01.00-py38", "stable"),
        ("2030.01.00-py38", "stable-py3"),
        ("2030.01.00-py38", "stable-py38"),
        ("2030.01.00-py38", "2030.01"),
        ("2030.01.00-py38", "2030.01.00-py38"),
        ("2030.01.01-py38", "2030.01.01-py38"),
        (f"bleeding-py38-rhel{rhel_version}", "bleeding"),
        (f"bleeding-py38-rhel{rhel_version}", "bleeding-py3"),
        (f"bleeding-py38-rhel{rhel_version}", "bleeding-py38"),
    ]
    return base_params


@pytest.mark.parametrize(
    "expect, name",
    generate_test_params_no_update(rhel_version()),
)
def test_resolve_no_update(komodo_root, expect, name):
    release, tracked = main.resolve_release(komodo_root, name, no_update=True)
    assert release == tracked
    assert release == komodo_root / expect
