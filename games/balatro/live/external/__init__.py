"""Lazy compatibility namespace for pre-v0.9 ``live.external`` imports.

Production modules live only in :mod:`games.balatro.live.runtime`.  Legacy imports
are resolved lazily to the canonical runtime module object so importing through
``live.external`` never loads a second copy of a runtime module and never eagerly
imports unrelated runtime modules during test collection.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys


_ALIAS_PREFIX = __name__ + "."
_RUNTIME_PREFIX = "games.balatro.live.runtime."


class _RuntimeAliasLoader(importlib.abc.Loader):
    def __init__(self, alias_name: str, canonical_name: str, canonical_spec) -> None:
        self.alias_name = alias_name
        self.canonical_name = canonical_name
        self.canonical_spec = canonical_spec

    def create_module(self, spec):
        return importlib.import_module(self.canonical_name)

    def exec_module(self, module) -> None:
        # ``create_module`` returns the already initialized canonical runtime
        # module. Keep both qualified names pointed at that exact object, then
        # restore canonical metadata that importlib temporarily replaced with the
        # compatibility alias spec.
        sys.modules[self.alias_name] = module
        module.__name__ = self.canonical_name
        module.__package__ = self.canonical_name.rpartition(".")[0]
        module.__spec__ = self.canonical_spec
        module.__loader__ = self.canonical_spec.loader
        if self.canonical_spec.submodule_search_locations is not None:
            module.__path__ = self.canonical_spec.submodule_search_locations


class _RuntimeAliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path=None, target=None):
        if not fullname.startswith(_ALIAS_PREFIX):
            return None

        canonical_name = _RUNTIME_PREFIX + fullname[len(_ALIAS_PREFIX) :]
        try:
            canonical_spec = importlib.util.find_spec(canonical_name)
        except (AttributeError, ImportError, ValueError):
            return None
        if canonical_spec is None:
            return None

        return importlib.util.spec_from_loader(
            fullname,
            _RuntimeAliasLoader(fullname, canonical_name, canonical_spec),
            origin=canonical_spec.origin,
            is_package=canonical_spec.submodule_search_locations is not None,
        )


# Direct ``from games.balatro.live.external import module`` imports can resolve
# without invoking submodule discovery at all. Cache the same canonical module
# under the legacy qualified name for subsequent direct-submodule imports.
def __getattr__(name: str):
    if name.startswith("_"):
        raise AttributeError(name)
    alias_name = f"{__name__}.{name}"
    canonical_name = f"{_RUNTIME_PREFIX}{name}"
    try:
        module = importlib.import_module(canonical_name)
    except ModuleNotFoundError as error:
        if error.name == canonical_name:
            raise AttributeError(name) from error
        raise
    sys.modules[alias_name] = module
    globals()[name] = module
    return module


sys.meta_path.insert(0, _RuntimeAliasFinder())

__all__: list[str] = []
