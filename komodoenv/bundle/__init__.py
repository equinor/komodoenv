from pathlib import Path


# Virtualenv provides several versions of these packages in order to support 2.7
# and 3.4. We don't support these Pythons so we only provide a single version for
# each package.
BUNDLES = {
    "pip": "pip-20.1.1-py2.py3-none-any.whl",
    "setuptools": "setuptools-47.3.1-py3-none-any.whl",
    "wheel": "wheel-0.34.2-py2.py3-none-any.whl",
}


def get_bundled_wheel(package: str) -> Path:
    """
    Returns path to a bundled wheel for 'package' (one of: pip, setuptools, wheel)
    """
    return Path(__file__).parent / BUNDLES[package]
