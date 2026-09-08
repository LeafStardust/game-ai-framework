from __future__ import annotations

"""Compatibility surface for native D1 Purple-Seal discard coverage.

Purple-Seal branch preservation now belongs directly to
``D1LiveBlindClearPlanner``. This module intentionally performs no production
class mutation; imports are retained for callers/tests that still reference the
old helper surface during the consolidation window.
"""

from games.balatro.live.hand_action_planner_core import (
    _eligible_purple_cards,
    _open_consumable_slots,
    _purple_generation_count,
)


def install_purple_seal_discard_policy() -> None:
    """Compatibility no-op; Purple-Seal beam coverage is native to D1."""
    return None


__all__ = (
    "_eligible_purple_cards",
    "_open_consumable_slots",
    "_purple_generation_count",
    "install_purple_seal_discard_policy",
)
