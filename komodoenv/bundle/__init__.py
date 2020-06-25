from pathlib import Path


BUNDLE_DIRECTORY = Path(__file__).absolute().parent
BUNDLE_SUPPORT = {
    "3.10": {
        "pip": "pip-20.1.1-py2.py3-none-any.whl",
        "setuptools": "setuptools-47.3.1-py3-none-any.whl",
        "wheel": "wheel-0.34.2-py2.py3-none-any.whl",
    },
    "3.9": {
        "pip": "pip-20.1.1-py2.py3-none-any.whl",
        "setuptools": "setuptools-47.3.1-py3-none-any.whl",
        "wheel": "wheel-0.34.2-py2.py3-none-any.whl",
    },
    "3.8": {
        "pip": "pip-20.1.1-py2.py3-none-any.whl",
        "setuptools": "setuptools-47.3.1-py3-none-any.whl",
        "wheel": "wheel-0.34.2-py2.py3-none-any.whl",
    },
    "3.7": {
        "pip": "pip-20.1.1-py2.py3-none-any.whl",
        "setuptools": "setuptools-47.3.1-py3-none-any.whl",
        "wheel": "wheel-0.34.2-py2.py3-none-any.whl",
    },
    "3.6": {
        "pip": "pip-20.1.1-py2.py3-none-any.whl",
        "setuptools": "setuptools-47.3.1-py3-none-any.whl",
        "wheel": "wheel-0.34.2-py2.py3-none-any.whl",
    },
    "3.5": {
        "pip": "pip-20.1.1-py2.py3-none-any.whl",
        "setuptools": "setuptools-47.3.1-py3-none-any.whl",
        "wheel": "wheel-0.34.2-py2.py3-none-any.whl",
    },
    "3.4": {
        "pip": "pip-19.1.1-py2.py3-none-any.whl",
        "setuptools": "setuptools-43.0.0-py2.py3-none-any.whl",
        "wheel": "wheel-0.33.6-py2.py3-none-any.whl",
    },
    "2.7": {
        "pip": "pip-20.1.1-py2.py3-none-any.whl",
        "setuptools": "setuptools-44.1.1-py2.py3-none-any.whl",
        "wheel": "wheel-0.34.2-py2.py3-none-any.whl",
    },
}

def get_embed_wheels(release):
    key = f"{release.majver}.{release.minver}"
    support = BUNDLE_SUPPORT.get(key)
    return [BUNDLE_DIRECTORY / fn for fn in support.values()]
