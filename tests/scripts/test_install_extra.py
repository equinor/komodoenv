import pytest
from pkg_resources import UnknownExtra
from komodoenv.scripts.install_extra import get_requires_for_package


def test_no_extra():
    with pytest.raises(UnknownExtra):
        get_requires_for_package("setuptools", "tests")


def test_single_extra():
    actual = get_requires_for_package("komodoenv", ["used_in_testing"])
    assert actual == [
        "test_some_package",
        "test_specific_version==1.2.3",
        "test_my_python",
        "test_some_linux_package",
    ]


def test_multi_extra():
    actual = get_requires_for_package("komodoenv", ["used_in_testing", "used_in_testing_too"])
    assert actual == [
        "test_some_package",
        "test_specific_version==1.2.3",
        "test_my_python",
        "test_some_linux_package",
        "test_additional_package>=4.2.0",
        "test_marker",
    ]
