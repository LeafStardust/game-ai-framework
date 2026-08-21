from __future__ import annotations

"""State-dependent relationship promotions learned from the latest five-run batch.

This layer wraps the existing public-state conditional relationship resolver. It
never patches tracker assessment/evaluation methods, so flat and tree-aware
trackers share one non-recursive assessment pipeline.
"""

from games.balatro import strategy_conditional_relationships as conditional
from games.balatro.strategy import GOLD


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _item_tokens(item: object) -> frozenset[str]:
    values = (
        type(item).__name__,
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "ability_name", ""),
    )
    return frozenset(token for value in values if (token := _normalize(value)))


def _owned_tokens(state) -> frozenset[str]:
    values: set[str] = set()
    for joker in getattr(state, "jokers", ()) or ():
        values.update(_item_tokens(joker))
    return frozenset(values)


def _throwback_scaled(state) -> bool:
    for joker in getattr(state, "jokers", ()) or ():
        if not (_item_tokens(joker) & {"throwback", "throwbackjoker"}):
            continue
        public = getattr(joker, "public_state", None)
        value = getattr(joker, "x_mult", None)
        if value is None and isinstance(public, dict):
            value = public.get("x_mult", 1.0)
        elif value is None and public is not None:
            value = getattr(public, "x_mult", 1.0)
        try:
            return float(value if value is not None else 1.0) > 1.0 + 1e-12
        except (TypeError, ValueError):
            return False
    return False


def install_latest_five_run_relationship_promotions() -> None:
    if getattr(conditional, "_latest_five_run_relationship_promotions_installed", False):
        return

    original = conditional.conditional_joker_relationship

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        tokens = _item_tokens(item)
        owned = _owned_tokens(state)

        # Walkie Talkie is only a defining Ten-Four core once Even Steven makes
        # the shared even-rank package materially stronger. Static Walkie and Even
        # relationships remain Silver.
        if (
            strategy_id == "ten_four"
            and tokens & {"walkietalkie", "walkietalkiejoker"}
            and owned & {"evensteven", "evenstevenjoker"}
        ):
            return GOLD

        # Throwback is ordinary Silver value at x1.0. Once public skip scaling has
        # actually increased its XMult, it becomes a realized Gold core.
        if (
            strategy_id == "throwback"
            and tokens & {"throwback", "throwbackjoker"}
            and _throwback_scaled(state)
        ):
            return GOLD

        return original(state, strategy_id, item)

    conditional.conditional_joker_relationship = conditional_joker_relationship
    conditional._latest_five_run_relationship_promotions_installed = True
