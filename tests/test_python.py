import sys

from komodoenv.python import Python


def test_init():
    py = Python(sys.executable, sys.prefix)

    assert str(py.executable) == sys.executable
    assert py.komodo_prefix == sys.prefix


def test_detect():
    py = Python(sys.executable, sys.prefix)
    py.detect()

    assert str(py.executable) == sys.executable
    assert py.komodo_prefix == sys.prefix
    assert str(py.site_packages_path) in sys.path
    assert py.version_info == sys.version_info


def test_ld_library_path():
    base = "/does/not/exist"
    py = Python(sys.executable, base)

    expect = f"{base}/lib64:{base}/lib\n".encode("utf-8")  # noqa UP012
    actual = py.call(script=b"import os;print(os.environ['LD_LIBRARY_PATH'])")
    assert expect == actual
