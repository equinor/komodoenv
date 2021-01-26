import sys
from textwrap import dedent
from komodoenv.python import Python, PythonType


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
    assert not py.is_shim()

    if hasattr(sys, "real_prefix"):
        assert py.type == PythonType.VENV
    else:
        assert py.type == PythonType.REAL


def test_ld_library_path():
    base = "/does/not/exist"
    py = Python(sys.executable, base)

    expect = "{0}/lib64:{0}/lib\n".format(base).encode("utf-8")
    actual = py.call(script=b"import os;print(os.environ['LD_LIBRARY_PATH'])")
    assert expect == actual


def test_shim(tmpdir):
    (tmpdir / "bin").mkdir()
    (tmpdir / "libexec").mkdir()

    with open(tmpdir / "bin" / "python", "w") as f:
        f.write(
            dedent(
                """\
        #!/bin/bash
        exec -a $0 $(dirname $0)/../libexec/python
        """
            )
        )

    (tmpdir / "bin" / "python").chmod(0o755)
    (tmpdir / "libexec" / "python").mksymlinkto(sys.executable)

    py = Python(str(tmpdir / "bin" / "python"), str(tmpdir))
    py.detect()

    assert py.is_shim()
