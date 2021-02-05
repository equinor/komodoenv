import argparse
import sys
import os
from typing import List, Optional

import pkg_resources


def parse_args(args: List[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("package")
    ap.add_argument("extras", nargs=argparse.REMAINDER)
    return ap.parse_args(args)


def get_requires_for_package(package: str, extras: List[str]) -> List[str]:
    dist = pkg_resources.get_distribution(package)
    print(
        f"The following extras are available for '{dist.project_name}': {', '.join(dist.extras)}",
        file=sys.stderr,
    )

    non_extra_pkgs = {x.project_name for x in dist.requires()}
    pkgs = dist.requires(extras=extras)

    install = []
    for pkg in pkgs:
        if pkg.project_name in non_extra_pkgs:
            continue
        if pkg.marker and not pkg.marker.evaluate(environment={"extra": True}):
            continue
        pkg.marker = None
        install.append(str(pkg))
    return install


def main(argv: Optional[List[str]] = None):
    """
    Usage: install_extra [PACKAGE] [EXTRAS...]

    Install _only_ the extras requires for the specified package, without
    installing the non-extra dependencies.
    """

    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    install = get_requires_for_package(args.package, args.extras)
    print("--- Installing the following dependencies ---", file=sys.stderr)
    print("\n".join(install), file=sys.stderr)

    print("--------------- Starting  pip ---------------", file=sys.stderr)
    os.execv(sys.executable, [sys.executable, "-m", "pip", "install", *install])


if __name__ == "__main__":
    main()
