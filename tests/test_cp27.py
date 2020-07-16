import sys
import pytest


if sys.version_info != (2, 7):
    pytest.skip("Skipping CPython 2.7 tests", allow_module_level=True)


def test_init(self):
    pass
