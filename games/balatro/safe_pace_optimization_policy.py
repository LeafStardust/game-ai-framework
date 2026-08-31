from __future__ import annotations

"""Bound the production D1 adaptive-search schedule for Red/White competence.

Safe-pace action arbitration is installed separately on the production
``StrategyAwareLiveHandActionPolicy`` by ``safe_pace_scope_correction``. This module
owns only the bounded advisory search schedule. The production path-aware D1 engine
applies it directly; importing this module does not patch base D1 behavior.
"""

from games.balatro.live.adaptive_search import (
    LIVE_ADAPTIVE_MAX_HORIZON,
    AdaptiveBlindSearchConfig,
)


def _safe_search_schedule(
    *,
    hands_remaining: int,
    discards_remaining: int,
    max_horizon: int = 8,
    max_nodes: int = 5000,
) -> tuple[AdaptiveBlindSearchConfig, ...]:
    """Keep ordinary D1 shallow while preserving literal final-hand recovery.

    Multi-hand states retain the single horizon-two advisory pass.  When exactly
    one scoring hand remains, however, every remaining discard is mechanically
    usable before that final hand without consuming it.  The advisory horizon must
    therefore be able to represent that bounded discard chain; otherwise D1 can
    commit its sole Play while legal recovery resources are still unused.
    """
    if hands_remaining < 0 or discards_remaining < 0:
        raise ValueError("remaining hands/discards cannot be negative")
    if hands_remaining + discards_remaining <= 0:
        return ()
    if max_horizon < 1 or max_nodes < 1:
        raise ValueError("search horizon/nodes must be positive")

    action_budget = hands_remaining + discards_remaining
    if hands_remaining == 1 and discards_remaining > 0:
        horizon = min(
            action_budget,
            int(max_horizon),
            LIVE_ADAPTIVE_MAX_HORIZON,
        )
    else:
        horizon = 1 if action_budget == 1 else 2

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
