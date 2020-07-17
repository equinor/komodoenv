from setuptools import setup


setup(
    name="komodoenv",
    version="0.1.0",
    packages=["komodoenv", "komodoenv.bundle", "komodoenv.versions"],
    test_suite="tests",
    install_requires=[
        "PyYAML",
        "enum34;python_version < '3.4'",
        "mock;python_version < '3.3'",
        "pathlib;python_version < '3.4'",
        "virtualenv",
        "six",
    ],
    entry_points={
        "console_scripts": [
            "komodoenv = komodoenv.main:main"
        ]
    }
)
