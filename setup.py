import sys
from pathlib import Path
from subprocess import check_output

from setuptools import setup


def download_bundled_wheels() -> None:
    dest = Path(__file__).parent / "komodoenv" / "bundle"
    print(f"Downloading wheels to {dest.resolve()}")
    check_output(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "pip",
            "setuptools",
            "wheel",
            "--dest",
            dest,
        ]
    )


download_bundled_wheels()

setup(
    name="komodoenv",
    author="Equinor ASA",
    author_email="fg_sib-scout@equinor.com",
    packages=["komodoenv", "komodoenv.bundle"],
    package_data={
        "komodoenv": ["bundle/*.whl"],
    },
    test_suite="tests",
    install_requires=[
        "ansicolors",
        "distro",
        "PyYAML",
    ],
    entry_points={"console_scripts": ["komodoenv = komodoenv.__main__:main"]},
    use_scm_version={"relative_to": __file__, "write_to": "komodoenv/_version.py"},
)
