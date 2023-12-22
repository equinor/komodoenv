# Komodoenv

Komodoenv is to a Komodo release as what
[virtualenv](https://pypi.org/project/virtualenv/) is to a Python installation.
Komodoenv creates a user-modifiable komodo environment based on an existing
komodo release, allowing users to install additional or updated packages without
the necessity for ugly hacks.

Komodoenv uses [virtualenv](https://pypi.org/project/virtualenv/) at its core.

## Usage

### Create
The easiest way to create a komodoenv is to first enable a komodo release.

```bash
$ source /prog/res/komodo/stable/enable
$ komodoenv my-kenv
```

Now you are able to source `my-kenv`:
```
$ source my-kenv/enable
$ which ert  # => [..]/my-kenv/root/shims/ert

$ # Install other packages, which you can use directly, or eg. in an ERT forward model
$ pip install my-package
```

Note that the newly created `my-kenv` is a fully-fledged komodo release, meaning
you don't need to enable the original before enabling `my-kenv`. In fact,
enabling `my-kenv` will disable the other komodo release.

## Update
Komodoenv doesn't automatically update your environment. It does check if
there's an update when enabling, and you'll often be able to run the
`komodoenv-update` command to update your environment to use the latest komodo
release packages.

## Development

### Installing
Komodoenv is meant to be part of a [komodo](https://github.com/equinor/komodo)
release. As such, it is not meant to be installed by users directly.

This project requires Python 3.8. Then, install this project with `pip install .`

### Testing
Komodoenv uses `pytest` for test running. Ensure that it's installed with `pip
install pytest`. To run tests:

``` bash
pytest tests/
```

