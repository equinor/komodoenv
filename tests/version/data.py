from pathlib import Path
from textwrap import dedent
from shutil import copy


def create_komodo(python_executable, libdir):
    root = Path.cwd()

    (root / "root" / "bin").mkdir_p()
    (root / "root" / "lib" / libdir / "site-packages").mkdir_p()

    copy(root / "root" / "bin" / "python")
