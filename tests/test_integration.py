import sys
from subprocess import PIPE, STDOUT, Popen, check_call, check_output
from textwrap import dedent

from komodoenv.__main__ import main as _main


def bash(script):
    return _run(("/bin/bash", "-eux"), script)


def csh(script):
    return _run(("/bin/csh", "-f"), script)


def test_test_bash():
    """Sanity test for testing bash"""
    assert bash("echo hello\necho world") == 0
    assert bash("exit 1") == 1
    assert bash("echo $OH_NO_AN_UNBOUND_VARIABLE") == 1
    assert bash("/bin/false;exit 0") == 1


def test_test_csh():
    """Sanity test for testing csh"""
    assert csh("echo hello\necho world") == 0
    assert csh("exit 1") == 1
    assert csh("echo $OH_NO_AN_UNBOUND_VARIABLE") == 1


def test_init_bash(komodo_root, tmp_path):
    main(
        "--root",
        str(komodo_root),
        "--release",
        "2030.01.00-py312",
        str(tmp_path / "kenv"),
    )

    script = """\
    source {kmd}/enable

    [[ $(which python) == "{kmd}/root/bin/python" ]]
    [[ $(python -c "import numpy;print(numpy.__version__)") == "1.26.0" ]]
    """.format(kmd=tmp_path / "kenv")

    assert bash(script) == 0


def test_init_csh(komodo_root, tmp_path):
    main(
        "--root",
        str(komodo_root),
        "--release",
        "2030.01.00-py312",
        str(tmp_path / "kenv"),
    )

    script = """\
    source {kmd}/enable.csh

    test `which python` = "{kmd}/root/bin/python" || exit 1
    test `python -c "import numpy;print(numpy.__version__)"` || exit 2
    """.format(kmd=tmp_path / "kenv")

    assert csh(script) == 0


def test_update(request, komodo_root, tmp_path):
    main(
        "--root",
        str(komodo_root),
        "--release",
        "2030.01-py312",
        str(tmp_path / "kenv"),
    )

    # Verify that komodo hasn't been updated
    check_output([str(tmp_path / "kenv/root/bin/komodoenv-update"), "--check"])

    # Update to 2030.01.01
    (komodo_root / "2030.01-py312").unlink()
    (komodo_root / "2030.01-py312").symlink_to("2030.01.01-py312")

    def revert():
        (komodo_root / "2030.01-py312").unlink()
        (komodo_root / "2030.01-py312").symlink_to("2030.01.00-py312")

    request.addfinalizer(revert)

    # There's now an update
    output = check_output(
        [str(tmp_path / "kenv/root/bin/komodoenv-update"), "--check"], stderr=STDOUT
    ).decode("utf-8")
    assert (
        "Warning: Your komodoenv is out of date. You will need to recreate komodo"
        in output
    )

    # Update
    script = """\
    set +e
    source {kmd}/enable
    set -e

    komodoenv-update
    """.format(kmd=tmp_path / "kenv")
    assert bash(script) == 0

    # Check that our numpy is updated
    script = """\
    source {kmd}/enable

    [[ $(which python) == "{kmd}/root/bin/python" ]]
    [[ $(python -c "import numpy;print(numpy.__version__)") == "1.26.4" ]]
    """.format(kmd=tmp_path / "kenv")
    assert bash(script) == 0


def test_autodetect(komodo_root, tmp_path):
    script = f"""\
    # Source komodo release and autodetect
    source {komodo_root}/stable/enable
    {sys.executable} -m komodoenv --root={komodo_root} {tmp_path}/kenv

    # Test
    source {tmp_path}/kenv/enable
    [[ $(which python) == "{tmp_path}/kenv/root/bin/python"  ]]
    """
    assert bash(script) == 0


def test_editable_install_takes_precedence_over_komodo(komodo_root, tmp_path):
    main(
        "--root",
        str(komodo_root),
        "--release",
        "2030.01.00-py312",
        str(tmp_path / "kenv"),
    )

    # A custom package-dir makes setuptools implement the editable install
    # with an import finder instead of a path in a .pth file
    project = tmp_path / "numpy"
    (project / "src/numpy").mkdir(parents=True)
    (project / "src/numpy/__init__.py").write_text('__version__ = "editable"\n')
    (project / "pyproject.toml").write_text(
        dedent(
            """\
            [build-system]
            requires = ["setuptools>=64"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "numpy"
            version = "2030.1"

            [tool.setuptools]
            packages = ["numpy"]
            package-dir = {numpy = "src/numpy"}
            """
        )
    )

    python = str(tmp_path / "kenv/root/bin/python")
    check_call([python, "-m", "pip", "install", "-e", str(project)])

    version = check_output([python, "-c", "import numpy;print(numpy.__version__)"])
    assert version.decode().strip() == "editable"


def main(*args):
    """Convenience function because it looks nicer"""
    _main(args)


def _run(args, script):
    proc = Popen(args, stdin=PIPE)
    proc.communicate(script.encode("utf-8"))
    return proc.returncode
