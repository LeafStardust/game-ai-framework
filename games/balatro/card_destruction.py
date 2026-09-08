from __future__ import annotations

"""Shared permanent playing-card destruction semantics.

Destruction is not an ordinary discard.  This module owns the public permanent
composition update and the currently modeled Joker reactions to destroyed playing
cards.  Transient hand/deck-area movement remains the caller's responsibility.
"""

from games.balatro.hand_rules import card_is_face, hand_rules_for_state


def _card_identity(card) -> tuple[str, object]:
    live_id = getattr(card, "live_id", None)
    if live_id is not None:
        return ("live", live_id)
    return ("object", id(card))


def _remove_destroyed_from_owned_deck(state, destroyed) -> None:
    owned_deck = getattr(state, "owned_deck", None)
    if owned_deck is None:
        return

    remaining = list(owned_deck)
    for card in destroyed:
        identity = _card_identity(card)
        for index, candidate in enumerate(remaining):
            if _card_identity(candidate) == identity:
                del remaining[index]
                break
    state.owned_deck = remaining


def project_destroyed_playing_cards(state, cards) -> tuple:
    """Apply permanent public-state consequences of playing-card destruction."""
    if state is None:
        return ()

    destroyed = []
    seen = set()
    for card in list(cards or []):
        identity = _card_identity(card)
        if identity in seen:
            continue
        seen.add(identity)
        destroyed.append(card)

    if not destroyed:
        return ()

    _remove_destroyed_from_owned_deck(state, destroyed)
    rules = hand_rules_for_state(state)
    glass_destroyed = sum(
        getattr(card, "enhancement", None) == "Glass"
        for card in destroyed
    )
    face_destroyed = sum(
        card_is_face(card, rules)
        for card in destroyed
    )

    if glass_destroyed:
        state.glass_cards_destroyed = (
            int(getattr(state, "glass_cards_destroyed", 0) or 0)
            + glass_destroyed
        )

    for joker in getattr(state, "jokers", []) or []:
        class_name = type(joker).__name__
        if class_name == "GlassJoker" and glass_destroyed:
            on_destroyed = getattr(joker, "on_glass_destroyed", None)
            if callable(on_destroyed):
                on_destroyed(glass_destroyed)
        elif class_name == "CanioJoker" and face_destroyed:
            joker.x_mult = (
                float(getattr(joker, "x_mult", 1.0) or 1.0)
                + face_destroyed
            )

    return tuple(destroyed)
