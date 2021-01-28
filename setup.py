from setuptools import setup


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
    extras_require={
        "testing": [
            "black",
            "mypy",
            "pytest",
        ]
    },
    entry_points={"console_scripts": ["komodoenv = komodoenv.__main__:main"]},
    use_scm_version={"relative_to": __file__, "write_to": "komodoenv/_version.py"},
)
