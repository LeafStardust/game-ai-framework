from __future__ import annotations

from games.balatro.joker import JokerContext


PASSIVE_HAND_RULE_JOKERS = frozenset(
    {
        "FourFingersJoker",
        "ShortcutJoker",
        "SplashJoker",
        "SmearedJoker",
    }
)


def hand_rules_for_state(state) -> dict:
    """Return public passive card/hand rules contributed by owned Jokers.

    Only passive rule Jokers are executed here. This keeps hand recognition free
    from scoring/state transitions while still making the 152 per-Joker mechanics
    files the source of truth for each Joker's declared rule.
    """
    if state is None:
        return {}

    context = JokerContext(
        state=state,
        trigger="HAND_RULES",
        data={},
    )
    for joker in getattr(state, "jokers", []):
        if type(joker).__name__ not in PASSIVE_HAND_RULE_JOKERS:
            continue
        context = joker.apply(context)
    return dict(context.data)
