from __future__ import annotations

from games.balatro.joker import JokerContext


PASSIVE_HAND_RULE_JOKERS = frozenset(
    {
        "FourFingersJoker",
        "ShortcutJoker",
        "SplashJoker",
    }
)


def hand_rules_for_state(state) -> dict:
    """Return admitted public passive card/hand rules from owned Jokers.

    Only passive rule Jokers already admitted by live score projection are executed
    here. This keeps hand recognition and projected scoring on the same fail-closed
    boundary while leaving each per-Joker mechanics file as the rule source of
    truth. Deferred rules are added here only when their live projection is exact.
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
