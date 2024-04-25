from pathlib import Path

BUNDLES = {
    wheel.name.split("-")[0]: wheel for wheel in Path(__file__).parent.glob("*.whl")
}


def get_bundled_wheel(package: str) -> Path:
    """
    Returns path to a bundled wheel for 'package' (one of: pip, setuptools, wheel)
    """
    return BUNDLES[package]
