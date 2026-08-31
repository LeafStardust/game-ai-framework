from __future__ import annotations

"""Compatibility surface for native D1 held round-end resource handling.

Blue-Seal round-end consumable generation and Gold-card preservation now belong to
``LiveBlindClearPlanner`` itself. This module intentionally performs no production
class mutation; the helpers remain available during the consolidation window for
callers and focused tests that still import the old surface.
"""


def _same_card(left, right) -> bool:
    left_id = getattr(left, "live_id", None)
    right_id = getattr(right, "live_id", None)
    if left_id is not None or right_id is not None:
        return left_id is not None and left_id == right_id
    return left == right


def _remaining_after_play(hand, selected) -> list:
    remaining = list(hand or ())
    for selected_card in tuple(selected or ()):
        for index, candidate in enumerate(remaining):
            if _same_card(candidate, selected_card):
                del remaining[index]
                break
    return remaining


def _active_gold(card) -> bool:
    return (
        str(getattr(card, "enhancement", "") or "") == "Gold"
        and not bool(getattr(card, "debuffed", False))
    )


def _active_blue(card) -> bool:
    return (
        str(getattr(card, "seal", "") or "") == "Blue"
        and not bool(getattr(card, "debuffed", False))
    )


def _blue_reward_count(state, held_cards) -> int:
    slots = max(0, int(getattr(state, "consumable_slots", 0) or 0))
    held_consumables = len(tuple(getattr(state, "consumables", ()) or ()))
    room = max(0, slots - held_consumables)
    if room <= 0:
        return 0
    blue = sum(1 for card in held_cards if _active_blue(card))
    return min(room, blue)


def install_held_round_end_resource_policy() -> None:
    """Compatibility no-op; held round-end resources are native to the planner."""
    return None


__all__ = (
    "_active_blue",
    "_active_gold",
    "_blue_reward_count",
    "_remaining_after_play",
    "_same_card",
    "install_held_round_end_resource_policy",
)
