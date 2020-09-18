from setuptools import setup


setup(
    name="komodoenv",
    packages=["komodoenv"],
    test_suite="tests",
    install_requires=[
        "ansicolors",
        "distro",
        "PyYAML",
        "enum34;python_version < '3.4'",
        "mock;python_version < '3.3'",
        "pathlib;python_version < '3.4'",
        "virtualenv",
        "six",
    ],
    entry_points={
        "console_scripts": [
            "komodoenv = komodoenv.__main__:main"
        ]
    },
    use_scm_version={
        "relative_to": __file__,
        "write_to": "komodoenv/_version.py"
    }
)
