from __future__ import annotations

"""Compatibility surface for native Cerulean Bell D1 mechanics.

Production legality and future forced-card branching now live directly in
``games.balatro.live.hand_action_planner``. This module intentionally installs
nothing; it only preserves the historical helper import used by deterministic
regression tests and external callers.
"""

from games.balatro.live.hand_action_planner import _cerulean_future_forced_branches

__all__ = ["_cerulean_future_forced_branches"]
