from __future__ import annotations

import importlib
import inspect
import re
import unicodedata
from pathlib import Path

from games.balatro.hand import PokerHand
from games.balatro.joker import Joker
from games.balatro.live.joker_state_contract import (
    all_observed_public_joker_state_fields,
    observed_public_joker_state_fields,
)


class LiveJokerFactory:
    """Resolve observable Balatro Joker metadata into framework Joker objects."""

    MODULE_ALIASES = {
        "8_ball": "eight_ball",
        "ceremonial": "dagger",
        "ceremonial_dagger": "dagger",
        # The base Balatro card named simply "Joker" is modeled by the reusable
        # FlatMultJoker class, whose canonical default is +4 Mult.
        "joker": "flat_mult",
    }

    # Only values already admitted by the explicit public-state contract can be
    # assigned to Joker model fields. The observer remains responsible for the
    # narrow per-Joker memory whitelist.
    PUBLIC_STATE_FIELDS = all_observed_public_joker_state_fields()
    CONSTRUCTOR_PUBLIC_STATE_FIELDS = {
        "rank",
        "suit",
    }

    RANKS = {
        "Ace": "A",
        "King": "K",
        "Queen": "Q",
        "Jack": "J",
        "T": "10",
    }
    SUITS = {
        "H": "Hearts",
        "D": "Diamonds",
        "C": "Clubs",
        "S": "Spades",
    }

    def create(self, data: dict):
        joker_class = self.resolve_class(data)
        if joker_class is None:
            return None

        public_state = data.get("public_state")
        if not isinstance(public_state, dict):
            public_state = {}

        constructor_kwargs = self._constructor_kwargs(joker_class, public_state)
        if constructor_kwargs is None:
            # Dynamic constructor state must be observed explicitly. Never guess a
            # Castle suit or Idol target merely to make a model constructible.
            return None

        try:
            joker = joker_class(**constructor_kwargs)
        except TypeError:
            return None

        for field in (
            "live_id",
            "area_index",
            "center",
            "label",
            "rarity",
            "edition",
            "cost",
            "sell_cost",
            "discovered",
        ):
            value = data.get(field)
            if value is not None:
                setattr(joker, field, value)

        allowed_fields = observed_public_joker_state_fields(joker_class.__name__)
        for field in allowed_fields:
            value = public_state.get(field)
            if value is None or not hasattr(joker, field):
                continue
            if not isinstance(value, (str, int, float, bool)):
                continue
            setattr(joker, field, self._normalize_public_state_value(field, value))

        return joker

    def resolve_class(self, data: dict) -> type[Joker] | None:
        """Resolve the modeled Joker class without constructing an instance."""
        return self._resolve_class(data)

    def _constructor_kwargs(
        self,
        joker_class: type[Joker],
        public_state: dict,
    ) -> dict[str, object] | None:
        try:
            signature = inspect.signature(joker_class)
        except (TypeError, ValueError):
            return {}

        kwargs: dict[str, object] = {}
        for parameter in signature.parameters.values():
            if parameter.kind not in (
                parameter.POSITIONAL_OR_KEYWORD,
                parameter.KEYWORD_ONLY,
            ):
                continue
            if parameter.default is not inspect.Parameter.empty:
                continue

            name = parameter.name
            if name not in self.CONSTRUCTOR_PUBLIC_STATE_FIELDS:
                return None
            value = public_state.get(name)
            if not isinstance(value, str) or not value:
                return None
            kwargs[name] = self._normalize_constructor_value(name, value)

        return kwargs

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

    def _normalize_constructor_value(self, name: str, value: str) -> str:
        if name == "rank":
            return self.RANKS.get(value, value)
        if name == "suit":
            return self.SUITS.get(value, value)
        return value

    def _normalize_public_state_value(self, name: str, value):
        if name == "target_hand" and isinstance(value, str):
            normalized = value.strip().upper().replace(" ", "_").replace("-", "_")
            aliases = {
                "HIGHCARD": "HIGH_CARD",
                "TWOPAIR": "TWO_PAIR",
                "THREEOFAKIND": "THREE_OF_A_KIND",
                "FOUROFAKIND": "FOUR_OF_A_KIND",
                "FULLHOUSE": "FULL_HOUSE",
                "STRAIGHTFLUSH": "STRAIGHT_FLUSH",
            }
            normalized = aliases.get(normalized.replace("_", ""), normalized)
            try:
                return PokerHand[normalized]
            except KeyError:
                return None
        if isinstance(value, str):
            return self._normalize_constructor_value(name, value)
        return value

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
