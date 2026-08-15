from __future__ import annotations

from games.balatro.joker import JokerContext


PASSIVE_HAND_RULE_JOKERS = frozenset(
    {
        "FourFingersJoker",
        "PareidoliaJoker",
        "ShortcutJoker",
        "SmearedJoker",
        "SplashJoker",
    }
)


def card_is_face(card, rules: dict | None = None) -> bool:
    """Return whether one public card counts as a face card under passive rules."""
    if bool((rules or {}).get("all_cards_are_face")):
        return True
    return str(getattr(card, "rank", "")) in {"J", "Q", "K"}


def hand_rules_for_state(state) -> dict:
    """Return public passive card/hand rules contributed by owned Jokers.

    Rules may be resolved before every contributing Joker is admitted by live score
    projection. Projection itself remains fail-closed until those Joker mechanics
    are explicitly added to its supported set.
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
