"""Conditional strategy support for Card Sharp.

Card Sharp is strong support for an established repeated poker-hand route, but it
must not seed every poker-hand strategy merely because it is owned.
"""

from __future__ import annotations

from games.balatro import strategy_conditional_relationships as conditional_module
from games.balatro.strategy import NEUTRAL, SILVER


_CARD_SHARP = "cardsharpjoker"
_HAND_STRATEGIES = frozenset(
    {
        "high_card",
        "pair",
        "two_pair",
        "three_kind",
        "straight",
        "flush",
        "full_house",
        "four_kind",
        "straight_flush",
        "five_kind",
        "flush_house",
        "flush_five",
    }
)


def _token(item: object) -> str:
    return "".join(character for character in type(item).__name__.lower() if character.isalnum())


def _high_card_established(state) -> bool:
    if conditional_module._hand_level_is_invested(state, "HIGH_CARD"):
        return True
    owned = conditional_module._owned_joker_tokens(state)
    if "stuntmanjoker" in owned:
        return True
    return conditional_module._baron_mime_held_engine_is_material(state)


def _hand_route_established(state, strategy_id: str) -> bool:
    if strategy_id == "high_card":
        return _high_card_established(state)
    if strategy_id == "pair":
        return conditional_module._pair_has_independent_commitment(state)
    if strategy_id == "two_pair":
        return conditional_module._two_pair_has_independent_commitment(state)
    if strategy_id in conditional_module._POKER_HAND_OBELISK_COMMITMENTS:
        return conditional_module._other_poker_hand_has_independent_commitment(
            state,
            strategy_id,
        )
    return False


def install_card_sharp_strategy_rules() -> None:
    if getattr(conditional_module, "_card_sharp_strategy_rules_installed", False):
        return

    original_conditional = conditional_module.conditional_joker_relationship
    original_authoritative = conditional_module._is_authoritative_conditional_relationship

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        if strategy_id in _HAND_STRATEGIES and _token(item) == _CARD_SHARP:
            return SILVER if _hand_route_established(state, strategy_id) else NEUTRAL
        return original_conditional(state, strategy_id, item)

    def _is_authoritative_conditional_relationship(strategy_id: str, item: object) -> bool:
        if strategy_id in _HAND_STRATEGIES and _token(item) == _CARD_SHARP:
            return True
        return original_authoritative(strategy_id, item)

    conditional_module.conditional_joker_relationship = conditional_joker_relationship
    conditional_module._is_authoritative_conditional_relationship = (
        _is_authoritative_conditional_relationship
    )
    conditional_module._card_sharp_strategy_rules_installed = True
