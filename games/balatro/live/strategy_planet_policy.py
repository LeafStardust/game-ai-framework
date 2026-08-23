from __future__ import annotations

from games.balatro.live.planet_policy import LivePlanetPolicy


class StrategyAwareLivePlanetPolicy(LivePlanetPolicy):
    """Compatibility wrapper for the historical strategy-aware planet policy.

    Planet intent and fit are now owned by LivePlanetPolicy. The retired
    categorical strategy tracker is intentionally not consulted.
    """

    def __init__(self, *args, strategy_tracker=None, **kwargs):
        super().__init__(*args, **kwargs)
