from pathlib import Path
from komodoenv.versions import CPython27
import subprocess
from textwrap import dedent
import shutil


def test_symlinks(tmpdir):
    with tmpdir.as_cwd():
        srcdir = Path("/prog/res/komodo/rpath-py27")
        py = CPython27(srcdir, "kenv")

        expect_files = {
            Path(x)
            for x in (
                "root/lib/python2.7/os.py",
                # "root/lib/python2.7/os.pyc",
                "root/lib/python2.7/lib-dynload",
            )
        }

        assert expect_files == set(py.get_symlinks())


def test_create_env(tmpdir):
    with tmpdir.as_cwd():
        srcdir = Path("/prog/res/komodo/rpath-py27")
        py = CPython27(srcdir, "kenv")
        py.create()

        activate = dedent(
            """\
        #!/bin/bash
        source $PWD/kenv/enable
        $PWD/kenv/bin/python "$@"
        """
        )

        pyscript = dedent(
            """\
        import sys
        print(sys.path)
        """
        )

        with open("run.sh", "w") as f:
            f.write(activate)
        with open("script.py", "w") as f:
            f.write(pyscript)

        run_sh = str(tmpdir / "run.sh")
        print(subprocess.check_output(["/bin/bash", run_sh, "script.py"]))
