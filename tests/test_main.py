import pytest

import komodoenv.__main__ as main
from tests.conftest import rhel_version


def generate_test_params_simple(rhel_version):
    return [
        ("2030.01.00-py311", "stable-py311", "stable"),
        ("2030.01.00-py311", "stable-py311", "stable-py3"),
        ("2030.01.00-py311", "stable-py311", "stable-py311"),
        ("2030.01.00-py311", "stable-py311", "2030.01"),
        ("2030.01.00-py311", "stable-py311", "2030.01.00-py311"),
        (f"bleeding-py311-rhel{rhel_version}", "bleeding-py311", "bleeding"),
        (f"bleeding-py311-rhel{rhel_version}", "bleeding-py311", "bleeding-py3"),
        (f"bleeding-py311-rhel{rhel_version}", "bleeding-py311", "bleeding-py311"),
        (f"2025.04.01-py311-rhel{rhel_version}-numpy1", "testing-py311", "testing"),
        (
            f"2025.04.01-py311-rhel{rhel_version}-numpy1",
            "testing-py311",
            "testing-py311",
        ),
    ]


@pytest.mark.parametrize(
    "expect, track_name, name",
    generate_test_params_simple(rhel_version()),
)
def test_resolve_simple(komodo_root, track_name, name, expect):
    release, tracked = main.resolve_release(root=komodo_root, name=name)
    assert release == komodo_root / expect
    assert tracked == komodo_root / track_name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "bleed",
        "bleeding-",
        "2030.03.00-py311",
        "2030.03.00-py311-rhel9",
        # Singular release
        "2030.01.01-py311",
    ],
)
def test_resolve_fail(komodo_root, name):
    with pytest.raises(SystemExit):
        main.resolve_release(root=komodo_root, name=name)


def test_resolve_fail_singular(komodo_root):
    """
    When making a komodoenv of a singular release without --no-update, inform
    the user and exit.
    """
    with pytest.raises(SystemExit) as exc:
        main.resolve_release(root=komodo_root, name="2030.01.01-py311")
    assert "--no-update" in str(exc.value)


def generate_test_params_no_update(rhel_version):
    return [
        ("2030.01.00-py311", "stable"),
        ("2030.01.00-py311", "stable-py3"),
        ("2030.01.00-py311", "stable-py311"),
        ("2030.01.00-py311", "2030.01"),
        ("2030.01.00-py311", "2030.01.00-py311"),
        ("2030.01.01-py311", "2030.01.01-py311"),
        (f"bleeding-py311-rhel{rhel_version}", "bleeding"),
        (f"bleeding-py311-rhel{rhel_version}", "bleeding-py3"),
        (f"bleeding-py311-rhel{rhel_version}", "bleeding-py311"),
        (f"2025.04.01-py311-rhel{rhel_version}-numpy1", "2025.04"),
        (f"2025.04.01-py311-rhel{rhel_version}-numpy1", "2025.04-py3"),
        (f"2025.04.01-py311-rhel{rhel_version}-numpy1", "2025.04-py311"),
        (f"2025.04.01-py311-rhel{rhel_version}-numpy1", "2025.04.01-py311"),
    ]


@pytest.mark.parametrize(
    "expect, name",
    generate_test_params_no_update(rhel_version()),
)
def test_resolve_no_update(komodo_root, expect, name):
    release, tracked = main.resolve_release(root=komodo_root, name=name, no_update=True)
    assert release == tracked
    assert release == komodo_root / expect
