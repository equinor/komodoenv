import sys

from komodoenv.python import Python


def test_init():
    py = Python(sys.executable)

    assert str(py.executable) == sys.executable
    assert str(py.release_root) == sys.prefix


def test_detect():
    py = Python(sys.executable)
    py.detect()

    assert str(py.executable) == sys.executable
    assert str(py.release_root) == sys.prefix
    assert str(py.site_packages_path) in sys.path
    assert py.version_info == sys.version_info[:2]


def test_ld_library_path():
    py = Python(sys.executable)

    expect = f"{sys.prefix}/lib64:{sys.prefix}/lib\n".encode("utf-8")  # noqa: UP012
    actual = py.call(script=b"import os;print(os.environ['LD_LIBRARY_PATH'])")
    assert expect == actual
