from __future__ import annotations

"""Compatibility surface for native Serpent redraw handling.

The reusable ``LiveBlindClearPlanner`` and integrated production D1 planner now
apply The Serpent's exact post-action draw count natively. This module retains the
pure helper for callers/tests but performs no production class mutation.
"""

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers


SERPENT_DRAW_COUNT = 3


def serpent_draw_count(state, ordinary_draw_count: int) -> int:
    """Return the exact post-action public draw count under The Serpent."""
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return max(0, int(ordinary_draw_count))
    if str(getattr(state, "boss_name", "") or "") == "The Serpent":
        return SERPENT_DRAW_COUNT
    return max(0, int(ordinary_draw_count))


def install_serpent_draw_policy() -> None:
    """Compatibility no-op; Serpent redraw semantics are native to D1 planners."""
    return None


__all__ = ["SERPENT_DRAW_COUNT", "serpent_draw_count", "install_serpent_draw_policy"]
