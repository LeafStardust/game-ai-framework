from __future__ import annotations

"""Safety correction for authoritative conditional relationship gating.

An authoritative downgrade is valid only when the conditional resolver has a path
to restore the relationship once the prerequisite is present. Keep a few legacy
static supports non-authoritative until such a resolver exists, while making the
shared Blueprint/Brainstorm copy-engine relationship authoritative everywhere its
core map already provides that restore path.
"""

from games.balatro import strategy_conditional_relationships as conditional_module


def _tokens(*names: str) -> frozenset[str]:
    values = set()
    for name in names:
        token = "".join(ch for ch in name.lower() if ch.isalnum())
        if token:
            values.add(token if token.endswith("joker") else token + "joker")
    return frozenset(values)


_NON_AUTHORITATIVE_UNTIL_RESTORABLE = {
    "dagger_sacrifice": _tokens("Riff-Raff", "Egg", "Gift Card", "Invisible Joker"),
    "madness_eternal": _tokens("Madness"),
    # The combined cash-scoring route deliberately activates from either Bull or
    # Bootstraps. Its current conditional pair helper only describes the stronger
    # both-owned state, so do not let that helper erase the one-core relationship.
    "cash_bull_bootstraps": _tokens("Bull", "Bootstraps", "Rocket", "To the Moon"),
}


def install_strategy_conditional_authority_correction() -> None:
    if getattr(conditional_module, "_conditional_authority_correction_installed", False):
        return

    original = conditional_module._is_authoritative_conditional_relationship

    def _is_authoritative_conditional_relationship(strategy_id: str, item: object) -> bool:
        token = conditional_module._item_token(item)
        if token in _NON_AUTHORITATIVE_UNTIL_RESTORABLE.get(strategy_id, frozenset()):
            return False

        # Part-14 copy support already has a complete restore path: Blueprint and
        # Brainstorm are Silver exactly when the strategy's defining core is owned.
        if (
            strategy_id in conditional_module._PART_FOURTEEN_COPY_CORES
            and token in conditional_module._COPY_ENGINE_TOKENS
        ):
            return True

        return original(strategy_id, item)

    conditional_module._is_authoritative_conditional_relationship = (
        _is_authoritative_conditional_relationship
    )
    conditional_module._conditional_authority_correction_installed = True
