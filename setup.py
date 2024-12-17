import sys
from pathlib import Path
from subprocess import check_output

from setuptools import setup


def download_bundled_wheels() -> None:
    dest = Path(__file__).parent / "src" / "komodoenv" / "bundle"
    print(f"Downloading wheels to {dest.resolve()}")
    check_output(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "pip>=24",
            "--dest",
            dest,
        ],
    )


download_bundled_wheels()

setup(
    package_dir={"": "src"},
    packages=["komodoenv", "komodoenv.bundle"],
    package_data={
        "komodoenv": ["bundle/*.whl"],
    },
)
