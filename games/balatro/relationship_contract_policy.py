from __future__ import annotations

"""Final conditional-relationship contract corrections.

Several feature policies wrap ``conditional_joker_relationship`` independently.
This final layer owns a small set of user-approved relationships whose semantics
must remain authoritative regardless of wrapper installation order.
"""

from games.balatro import strategy_conditional_relationships as conditional_module
from games.balatro.strategy import GOLD, NEUTRAL, SILVER


_LOW_RANK_RETRIGGER_SUPPORT = frozenset(
    {"hangingchadjoker", "seltzerjoker", "duskjoker"}
)


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _token(item: object) -> str:
    type_token = _normalize(type(item).__name__)
    if type_token and type_token not in {"simplenamespace", "object"}:
        return type_token if type_token.endswith("joker") else type_token + "joker"
    for value in (
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "ability_name", ""),
    ):
        token = _normalize(value)
        if token:
            return token if token.endswith("joker") else token + "joker"
    return type_token


def _owned_tokens(state) -> frozenset[str]:
    return frozenset(_token(joker) for joker in getattr(state, "jokers", ()) or ())


def install_relationship_contract_policy() -> None:
    if getattr(conditional_module, "_relationship_contract_policy_installed", False):
        return

    original = conditional_module.conditional_joker_relationship

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        token = _token(item)
        owned = _owned_tokens(state)

        # Scholar is meaningful Aces evidence by itself, but DNA is the pairing that
        # upgrades Scholar to the strongest relationship tier.
        if strategy_id == "aces" and token == "scholarjoker":
            return GOLD if "dnajoker" in owned else SILVER

        # Played-card retriggers do not establish Low-Rank Scoring on their own.
        # Hack is the actual low-rank retrigger engine; without Hack these Jokers
        # remain neutral even if deck shape or Fibonacci points toward low ranks.
        if strategy_id == "low_rank" and token in _LOW_RANK_RETRIGGER_SUPPORT:
            return SILVER if "hackjoker" in owned else NEUTRAL

        return original(state, strategy_id, item)

    conditional_module.conditional_joker_relationship = conditional_joker_relationship
    conditional_module._relationship_contract_policy_installed = True
