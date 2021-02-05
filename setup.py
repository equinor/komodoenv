from setuptools import setup


setup(
    name="komodoenv",
    author="Equinor ASA",
    author_email="fg_sib-scout@equinor.com",
    packages=["komodoenv", "komodoenv.bundle", "komodoenv.scripts"],
    package_data={
        "komodoenv": ["bundle/*.whl"],
    },
    test_suite="tests",
    install_requires=[
        "PyYAML",
        "ansicolors",
        "distro",
        "setuptools"  # pkg_resources
    ],
    extras_require={
        # These extras are made for unit testing of komodoenv, not to be
        # installed by any user.
        "used_in_testing": [
            "test_my_python; python_version > '3.0'",
            "test_new_python; python_version >= '5.1'",
            "test_old_python; python_version < '2.7'",
            "test_some_fake_package; sys_platform == 'fakeos'",
            "test_some_linux_package; sys_platform == 'linux'",
            "test_some_macos_package; sys_platform == 'osx'",
            "test_some_package",
            "test_specific_version == 1.2.3",
        ],
        "used_in_testing_too": [
            "test_additional_package >= 4.2.0",
            "test_deactivated_marker; python_version >= '4.2'",
            "test_marker; python_version >= '1.2'",
        ],
    },
    entry_points={"console_scripts": ["komodoenv = komodoenv.__main__:main"]},
    use_scm_version={"relative_to": __file__, "write_to": "komodoenv/_version.py"},
)
