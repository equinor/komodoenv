import pytest
from komodoenv.versions import *


def test_factory_invalid():
    with pytest.raises(NotImplementedError):
        get_creator_for_version((2, 6))


def test_factory_cp27():
    assert get_creator_for_version((2, 7)) == CPython27
