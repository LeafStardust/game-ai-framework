from __future__ import annotations

"""State-dependent relationship promotions learned from the latest five-run batch.

The promotion must be visible in both owned-item assessment and candidate relationship
mapping.  Patch those two state-aware relationship surfaces directly; never call
``observe`` and never wrap private tracker assessment methods, so tree-aware tracking
retains one non-recursive assessment pipeline.
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


def _promotion(state, strategy_id: str, item: object) -> str | None:
    tokens = _item_tokens(item)
    owned = _owned_tokens(state)
    if (
        strategy_id == "ten_four"
        and tokens & {"walkietalkie", "walkietalkiejoker"}
        and owned & {"evensteven", "evenstevenjoker"}
    ):
        return GOLD
    if (
        strategy_id == "throwback"
        and tokens & {"throwback", "throwbackjoker"}
        and _throwback_scaled(state)
    ):
        return GOLD
    return None


def install_latest_five_run_relationship_promotions() -> None:
    if getattr(conditional, "_latest_five_run_relationship_promotions_installed", False):
        return

    original_view_relationship = conditional._ConditionalDefinitionView.relationship_for

    def relationship_for(self, item: object, *, kind: str) -> str:
        if str(kind).upper() == "JOKER":
            promoted = _promotion(self._state, self._definition.strategy_id, item)
            if promoted is not None:
                return promoted
        return original_view_relationship(self, item, kind=kind)

    conditional._ConditionalDefinitionView.relationship_for = relationship_for

    original_relationships_for = conditional.StateAwareBalatroStrategyTracker._relationships_for

    def _relationships_for(self, item: object, *, kind: str) -> dict[str, str]:
        found = original_relationships_for(self, item, kind=kind)
        if str(kind).upper() != "JOKER" or self._relationship_state is None:
            return found
        for strategy_id in self.definitions:
            promoted = _promotion(self._relationship_state, strategy_id, item)
            if promoted is not None:
                found[strategy_id] = promoted
        return found

    conditional.StateAwareBalatroStrategyTracker._relationships_for = _relationships_for
    conditional._latest_five_run_relationship_promotions_installed = True
