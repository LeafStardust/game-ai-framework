from __future__ import annotations

"""Conditional cash-generation support for the Bull/Bootstraps scoring route.

Money generators are not independent win conditions. They become strategy evidence
only after Bull or Bootstraps exists to convert banked cash into Chips/Mult.
"""

from games.balatro.strategy import GOLD, NEUTRAL, SILVER
from games.balatro import strategy_conditional_relationships as relationships


_CASH_SCORING_ID = "cash_bull_bootstraps"
_CASH_SCORING_CORES = frozenset({"bulljoker", "bootstrapsjoker"})
_DIRECT_CASH_SUPPORT = frozenset(
    {
        "rocketjoker",
        "tothemoonjoker",
        "cloud9joker",
        "satellitejoker",
        "reservedparkingjoker",
        "businesscardjoker",
        "facelessjoker",
        "mailinrebatejoker",
        "delayedgratificationjoker",
        "goldenjoker",
        "goldenticketjoker",
        "roughgemjoker",
    }
)


def _owned_tokens(state) -> frozenset[str]:
    return relationships._owned_joker_tokens(state)


def _token(item: object) -> str:
    return relationships._item_token(item)


def install_cash_scoring_support_policy() -> None:
    if getattr(relationships, "_cash_scoring_support_installed", False):
        return

    original = relationships.conditional_joker_relationship

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        base = original(state, strategy_id, item)
        if strategy_id != _CASH_SCORING_ID:
            return base

        owned = _owned_tokens(state)
        if not (owned & _CASH_SCORING_CORES):
            # Cash generation alone must never manufacture a scoring strategy.
            return base

        token = _token(item)
        if token in _CASH_SCORING_CORES:
            return GOLD

        if token in {"rocketjoker", "tothemoonjoker"}:
            partner = "tothemoonjoker" if token == "rocketjoker" else "rocketjoker"
            return GOLD if partner in owned else SILVER

        if token in _DIRECT_CASH_SUPPORT:
            return SILVER

        return base

    relationships.conditional_joker_relationship = conditional_joker_relationship
    relationships._cash_scoring_support_installed = True
