from __future__ import annotations

"""Compatibility surface for The Hook planner integration.

The scoring transition model owns The Hook's random forced-discard branches, and
``LiveBlindClearPlanner`` now consumes those branch-specific post-discard states
natively when refilling and continuing search. No planner class mutation remains
here.
"""

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers


def _hook_active(state) -> bool:
    return (
        state is not None
        and str(getattr(state, "boss_name", "") or "") == "The Hook"
        and not boss_blind_disabled_by_owned_jokers(state)
    )


def _same_card(left, right) -> bool:
    left_id = getattr(left, "live_id", None)
    right_id = getattr(right, "live_id", None)
    if left_id is not None or right_id is not None:
        return left_id is not None and left_id == right_id
    return left == right


def _remove_selected_cards(source, selected) -> list:
    remaining = list(source or [])
    for selected_card in list(selected or []):
        for index, candidate in enumerate(remaining):
            if _same_card(candidate, selected_card):
                del remaining[index]
                break
    return remaining


def install_hook_planner_integration_policy() -> None:
    """Compatibility no-op; Hook branch refill is native to the base planner."""
    return None
