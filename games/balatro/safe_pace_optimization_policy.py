from __future__ import annotations

"""Bound the production D1 adaptive-search schedule for Red/White competence.

Safe-pace action arbitration is installed separately on the production
``StrategyAwareLiveHandActionPolicy`` by ``safe_pace_scope_correction``. This module
owns only the bounded advisory search schedule. The production path-aware D1 engine
applies it directly; importing this module does not patch base D1 behavior.
"""

from games.balatro.live.adaptive_search import AdaptiveBlindSearchConfig


def _safe_search_schedule(
    *,
    hands_remaining: int,
    discards_remaining: int,
    max_horizon: int = 8,
    max_nodes: int = 5000,
) -> tuple[AdaptiveBlindSearchConfig, ...]:
    """One shallow advisory pass; never engineer a five-action clear line live."""
    if hands_remaining < 0 or discards_remaining < 0:
        raise ValueError("remaining hands/discards cannot be negative")
    if hands_remaining + discards_remaining <= 0:
        return ()
    if max_horizon < 1 or max_nodes < 1:
        raise ValueError("search horizon/nodes must be positive")

    horizon = 1 if hands_remaining + discards_remaining == 1 else 2
    return (
        AdaptiveBlindSearchConfig(
            horizon=horizon,
            samples=8,
            child_samples=1,
            play_width=3,
            discard_width=2 if discards_remaining > 0 else 0,
            child_play_width=1,
            child_discard_width=1 if discards_remaining > 0 else 0,
            max_nodes=min(int(max_nodes), 750),
        ),
    )
