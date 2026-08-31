from __future__ import annotations

"""Shared evidence for the production D1 wall-clock budget.

Live Red/White evidence showed canonical Hook adaptive search consuming essentially
an entire ordinary D1 wall-clock budget while producing no completed root. The
production D1 engine owns application of the shorter Hook budget directly and also
reserves a bounded slice of that effective budget for deterministic timeout recovery.
This module retains only the boss-state predicate and calibrated budget helpers used
by that engine and by bounded candidate shaping.
"""

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers


_HOOK_MAX_SEARCH_SECONDS = 3.0


def _active_hook(state) -> bool:
    return (
        str(getattr(state, "boss_name", "") or "") == "The Hook"
        and not boss_blind_disabled_by_owned_jokers(state)
    )


def _reserve_d1_fallback_seconds(configured_seconds: float | None) -> float | None:
    """Reserve deterministic timeout-recovery time from an effective D1 budget."""
    if configured_seconds is None or float(configured_seconds) <= 1.25:
        return configured_seconds
    configured = float(configured_seconds)
    reserve = min(1.0, max(0.50, configured * 0.125))
    return max(0.25, configured - reserve)


def effective_d1_search_seconds(state, configured_seconds: float | None) -> float | None:
    """Return the canonical search budget after boss caps and fallback reserve."""
    effective = configured_seconds
    if effective is not None and _active_hook(state):
        effective = min(float(effective), _HOOK_MAX_SEARCH_SECONDS)
    return _reserve_d1_fallback_seconds(effective)
