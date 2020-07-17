import sys
from six import ensure_binary
from komodoenv.context import Context


def test_invoke_python():
    ctx = Context("/usr")

    out = ctx.invoke_python(sys.executable, ["-c", "print('Test')"])
    assert out == b"Test\n"


def test_invoke_python_script():
    ctx = Context("/usr")
    script = b"import sys;print(sys.executable)"

    out = ctx.invoke_python(sys.executable, script=script)
    assert out == ensure_binary("{}\n".format(sys.executable))


def test_invoke_srcpython_script():
    pass
