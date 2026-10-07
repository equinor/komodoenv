"""Let editable installs in a komodoenv take precedence over komodo's packages.

Some editable installs, e.g. by setuptools for projects with a custom
package-dir, are implemented by an import finder appended to sys.meta_path,
which comes after the PathFinder that finds the package in komodo instead.

This module is copied into the komodoenv's site-packages and installed by
zzz_komodo.pth, so it must not depend on komodoenv.
"""

import sys
from collections.abc import Sequence
from importlib.machinery import ModuleSpec, PathFinder
from pathlib import Path
from types import ModuleType

# Modules of the finders installed by setuptools and the editables package
EDITABLE_FINDER_MODULES = ("__editable__", "editables")


class EditableOverKomodoFinder:
    def __init__(self, komodo_paths: Sequence[str]) -> None:
        self.komodo_paths = [Path(path) for path in komodo_paths]

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        spec = editable_spec(fullname, path, target)
        if spec is not None and self.is_from_komodo(
            PathFinder.find_spec(fullname, path, target)
        ):
            return spec
        return None

    def is_from_komodo(self, spec: ModuleSpec | None) -> bool:
        return (
            spec is not None
            and spec.origin is not None
            and any(Path(spec.origin).is_relative_to(p) for p in self.komodo_paths)
        )


def editable_spec(
    fullname: str, path: Sequence[str] | None, target: ModuleType | None
) -> ModuleSpec | None:
    for finder in sys.meta_path:
        if getattr(finder, "__module__", "").startswith(EDITABLE_FINDER_MODULES):
            spec = finder.find_spec(fullname, path, target)
            # Namespace packages are left to PathFinder, which merges all portions
            if spec is not None and spec.loader is not None:
                return spec
    return None


def install(komodo_paths: Sequence[str]) -> None:
    if not any(isinstance(f, EditableOverKomodoFinder) for f in sys.meta_path):
        sys.meta_path.insert(
            sys.meta_path.index(PathFinder), EditableOverKomodoFinder(komodo_paths)
        )
