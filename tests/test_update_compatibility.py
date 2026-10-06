import runpy
import shutil
from contextlib import redirect_stderr, suppress
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


@patch.dict("sys.modules", {"distro": None})
@patch("platform.release", lambda: "4.18.0.el8")
def test_standalone_update():
    source = Path(__file__).resolve().parents[1] / "src" / "komodoenv" / "update.py"
    site_packages = "root/lib/python3.12/site-packages"
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        komodo_root = root / "komodo"
        release = komodo_root / "2030.01.00-py312"
        (release / "root/bin").mkdir(parents=True)
        (release / "root/bin/example").write_text(
            "#!/usr/bin/python3\nprint('example')\n", encoding="utf-8"
        )
        (release / site_packages / "komodoenv-1.0.0.dist-info").mkdir(parents=True)
        (release / "enable").write_text(
            'CUSTOM_COORDINATE="-numpy1"\n', encoding="utf-8"
        )
        (komodo_root / "stable-py312").symlink_to(release.name)

        env = root / "kenv"
        updater = env / "root/bin/komodoenv-update"
        updater.parent.mkdir(parents=True)
        shutil.copyfile(source, updater)
        (env / site_packages).mkdir(parents=True)
        (env / "komodoenv.conf").write_text(
            f"komodo-root = {komodo_root}\n"
            "current-release = old\n"
            "tracked-release = stable-py312\n"
            "mtime-release = 0\n"
            "python-version = 3.12\n"
            "komodoenv-version = 1.0.0\n"
            "linux-dist = rhel8\n",
            encoding="utf-8",
        )

        namespace = runpy.run_path(str(updater))

        with redirect_stderr(StringIO()) as stderr, suppress(SystemExit):
            namespace["main"](["--check"])
        assert f"latest komodo release ({release.name})" in stderr.getvalue()

        namespace["main"]([])
        assert namespace["read_config"]()["current-release"] == release.name


if __name__ == "__main__":
    try:
        test_standalone_update()
    except SystemExit as error:
        msg = "Updater exited before completing the compatibility check"
        raise RuntimeError(msg) from error
