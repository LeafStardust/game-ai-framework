from __future__ import annotations

import importlib
import inspect
import re
import unicodedata
from pathlib import Path

from games.balatro.joker import Joker


class LiveJokerFactory:
    """Resolve observable Balatro Joker metadata into framework Joker objects."""

    MODULE_ALIASES = {
        "8_ball": "eight_ball",
    }

    # These fields are only accepted from the observer's narrowly whitelisted
    # ``public_state`` object, never from a broad raw ability blob.
    PUBLIC_STATE_FIELDS = {
        "chips",
        "chip_mod",
    }

    def create(self, data: dict):
        joker_class = self._resolve_class(data)
        if joker_class is None:
            return None

        try:
            joker = joker_class()
        except TypeError:
            return None

        for field in (
            "live_id",
            "area_index",
            "center",
            "label",
            "edition",
            "cost",
            "sell_cost",
        ):
            value = data.get(field)
            if value is not None:
                setattr(joker, field, value)

        public_state = data.get("public_state")
        if isinstance(public_state, dict):
            for field in self.PUBLIC_STATE_FIELDS:
                value = public_state.get(field)
                if (
                    value is not None
                    and hasattr(joker, field)
                    and isinstance(value, (int, float))
                    and not isinstance(value, bool)
                ):
                    setattr(joker, field, value)

        return joker

    def _resolve_class(self, data: dict) -> type[Joker] | None:
        for module_name in self._module_candidates(data):
            if not self._module_exists(module_name):
                continue

            module = importlib.import_module(
                f"games.balatro.jokers.{module_name}"
            )
            candidates = [
                value
                for value in vars(module).values()
                if inspect.isclass(value)
                and value is not Joker
                and issubclass(value, Joker)
                and value.__module__ == module.__name__
                and not inspect.isabstract(value)
            ]
            if len(candidates) == 1:
                return candidates[0]

        return None

    def _module_candidates(self, data: dict) -> list[str]:
        candidates: list[str] = []

        label = data.get("label") or data.get("ability_name")
        if isinstance(label, str) and label:
            candidates.append(self._slug(label))

        center = data.get("center") or data.get("key")
        if isinstance(center, str) and center.startswith("j_"):
            candidates.append(center[2:])

        expanded: list[str] = []
        for candidate in candidates:
            if not candidate:
                continue
            expanded.append(candidate)
            alias = self.MODULE_ALIASES.get(candidate)
            if alias is not None:
                expanded.append(alias)
            if not candidate.endswith("_joker"):
                expanded.append(f"{candidate}_joker")
            if not candidate.startswith("the_"):
                expanded.append(f"the_{candidate}")

        return list(dict.fromkeys(expanded))

    @staticmethod
    def _slug(value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value).encode(
            "ascii", "ignore"
        ).decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value).strip("_").lower()
        return slug

    @staticmethod
    def _module_exists(module_name: str) -> bool:
        module_path = Path(__file__).parents[1] / "jokers" / f"{module_name}.py"
        return module_path.is_file()
