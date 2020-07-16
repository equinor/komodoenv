import sys
import os
from stat import ST_MODE, S_IFREG
from komodoenv import actions
from pathlib import Path


if sys.version_info >= (3, 3):
    from unittest.mock import Mock
else:
    from mock import Mock


def test_install_wheel():
    ctx = Mock()
    act = actions.InstallWheel("/")
    act.install(ctx)
    ctx.pip_install.assert_called_once()


def test_create(tmpdir):
    with tmpdir.as_cwd():
        ctx = Mock()
        ctx.dry_run = False
        ctx.dstpath = Path(str(tmpdir / "dst"))

        act = actions.Create("testfile", "TEST", 0o765)
        act.start(ctx)

        path = ctx.dstpath / "testfile"
        assert path.exists()

        # Check that the file is a Regular file and has mode 0765
        assert os.stat(str(path))[ST_MODE] == (S_IFREG | 0o765)

        # Test contents
        with open(str(path)) as f:
            assert f.read() == "TEST"


def test_create_mkdir(tmpdir):
    relpath = "foo/bar/a/b/c/testfile"
    with tmpdir.as_cwd():
        ctx = Mock()
        ctx.dry_run = False
        ctx.dstpath = Path(str(tmpdir / "dst"))

        act = actions.Create(relpath, "TEST", 0o623)
        act.start(ctx)

        path = ctx.dstpath / relpath
        assert path.exists()

        # Check that the file is a Regular file and has mode 0623
        assert os.stat(str(path))[ST_MODE] == (S_IFREG | 0o623)

        # Test contents
        with open(str(path)) as f:
            assert f.read() == "TEST"


def test_copy(tmpdir):
    with tmpdir.as_cwd():
        ctx = Mock()
        ctx.dry_run = False
        ctx.srcpath = Path(str(tmpdir / "src"))
        ctx.dstpath = Path(str(tmpdir / "dst"))

        ctx.srcpath.mkdir()
        with open(str(ctx.srcpath / "test"), "w") as f:
            f.write("TEST")

        act = actions.Copy("test")
        act.start(ctx)

        path = ctx.dstpath / "test"
        assert path.exists()

        with open(str(path)) as f:
            assert f.read() == "TEST"


def test_symlink(tmpdir):
    with tmpdir.as_cwd():
        ctx = Mock()
        ctx.dry_run = False
        ctx.srcpath = Path(str(tmpdir / "src"))
        ctx.dstpath = Path(str(tmpdir / "dst"))

        ctx.srcpath.mkdir()
        with open(str(ctx.srcpath / "test"), "w") as f:
            f.write("TEST")

        act = actions.Symlink("test")
        act.start(ctx)

        path = ctx.dstpath / "test"
        assert path.exists()

        with open(str(path)) as f:
            assert f.read() == "TEST"

        assert path.resolve() == (ctx.srcpath / "test")


def test_dry_run(capsys, tmpdir):
    with tmpdir.as_cwd():
        ctx = Mock()
        ctx.dry_run = True

        act = actions.Copy("/bin/bash")
        act.start(ctx)

        out, err = capsys.readouterr()
        assert out == "Copy: /bin/bash\n"
        assert len(err) == 0

        # Check that tmpdir is empty (we haven't copied any files)
        assert os.listdir(str(tmpdir)) == []


def test_libexec_shim(tmpdir):
    print(type(tmpdir))

    assert False

    with tmpdir.as_cwd():
        ctx = Mock()
        ctx.dry_run = False
        ctx.dstpath = Path(str(tmpdir / "dst"))
