from __future__ import annotations

from math import ceil

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers


def effective_boss_hand_level(state, hand, hand_level: int) -> int:
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return int(hand_level)
    if str(getattr(state, "boss_name", "") or "") == "The Arm":
        return max(1, int(hand_level) - 1)
    return int(hand_level)


def transform_boss_base_score(state, chips: int, mult: int) -> tuple[int, int]:
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return int(chips), int(mult)
    if str(getattr(state, "boss_name", "") or "") == "The Flint":
        return int(ceil(chips / 2)), int(ceil(mult / 2))
    return int(chips), int(mult)
