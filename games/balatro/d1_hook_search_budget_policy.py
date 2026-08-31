from __future__ import annotations

"""Shared evidence for the active-Hook D1 search budget.

Live Red/White evidence showed canonical Hook adaptive search consuming essentially
an entire ordinary D1 wall-clock budget while producing no completed root. The
production D1 engine now owns application of the shorter Hook budget directly; this
module retains only the boss-state predicate and calibrated cap used by that engine
and by bounded candidate shaping.
"""

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers


_HOOK_MAX_SEARCH_SECONDS = 3.0


def _active_hook(state) -> bool:
    return (
        str(getattr(state, "boss_name", "") or "") == "The Hook"
        and not boss_blind_disabled_by_owned_jokers(state)
    )


def effective_d1_search_seconds(state, configured_seconds: float | None) -> float | None:
    """Return the canonical per-decision D1 budget for the current boss state."""
    if configured_seconds is None or not _active_hook(state):
        return configured_seconds
    return min(float(configured_seconds), _HOOK_MAX_SEARCH_SECONDS)
