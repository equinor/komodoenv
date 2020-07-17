import sys
import os
import pytest
import subprocess
from stat import ST_MODE, S_IFREG
from textwrap import dedent
from pathlib import Path
from komodoenv import creator


if sys.version_info >= (3, 3):
    from unittest.mock import Mock
else:
    from mock import Mock


def test_generate_enable_script():
    fmt = dedent("""\
    {komodo_prefix}
    {komodo_release}
    {komodoenv_prefix}
    {komodoenv_release}
    """)

    expect = dedent("""\
    /prog/res/komodo/stable/root
    stable
    /private/unittest/kenv/root
    kenv
    """)

    ctx = Mock()
    ctx.srcpath = Path("/prog/res/komodo/stable")
    ctx.dstpath = Path("/private/unittest/kenv")
    assert creator.generate_enable_script(ctx, fmt) == expect


def test_create_enable_scripts(tmpdir):
    with tmpdir.as_cwd():
        ctx = Mock()
        ctx.srcpath = Path("/prog/res/komodo/stable")
        ctx.dstpath = Path(str(tmpdir / "kenv"))
        ctx.dstpath.mkdir()

        creator.create_enable_scripts(ctx)
        assert (ctx.dstpath / "enable").exists()
        assert (ctx.dstpath / "enable.csh").exists()


@pytest.mark.skip("")
def test_create_virtualenv():
    pass


def test_update_script(tmpdir, monkeypatch):
    with tmpdir.as_cwd():
        ctx = Mock()
        ctx.dstpath = tmpdir / "kenv"
        ctx.dstpath.mkdir()

        def check_output(*args, **kwargs):
            pass

        monkeypatch.setattr(subprocess, "check_output", check_output)
        creator.copy_update_script(ctx)
        assert (ctx.dstpath / "komodo-update").exists()


def test_config(tmpdir):
    with tmpdir.as_cwd():
        ctx = Mock()
        ctx.dstpath = tmpdir / "kenv"
        ctx.dstpath.mkdir()

        creator.create_config(ctx)


def test_pth(tmpdir):
    with tmpdir.as_cwd():
        ctx = Mock()
        ctx.dstpath = tmpdir / "kenv"
        ctx.dstpath.mkdir()
        ctx.src_python_paths = sys.path
        ctx.dst_python_libpath = ctx.dstpath
        (ctx.dst_python_libpath / "site-packages").mkdir()

        creator.create_pth(ctx)


def test_shim_pythons(tmpdir):
    pass
