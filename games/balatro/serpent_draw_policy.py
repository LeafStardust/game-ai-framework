from __future__ import annotations

"""Compatibility helpers for The Serpent's native D1 draw mechanic.

Production D1 now models this directly in ``D1LiveBlindClearPlanner``. This module
installs nothing and exists only for deterministic helper-level regressions.
"""

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers

SERPENT_DRAW_COUNT = 3


def serpent_draw_count(state, ordinary_draw_count: int) -> int:
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return max(0, int(ordinary_draw_count))
    if str(getattr(state, "boss_name", "") or "") == "The Serpent":
        return SERPENT_DRAW_COUNT
    return max(0, int(ordinary_draw_count))


__all__ = ["SERPENT_DRAW_COUNT", "serpent_draw_count"]
