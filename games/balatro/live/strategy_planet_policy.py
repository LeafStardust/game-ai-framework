from __future__ import annotations

from games.balatro.live.planet_policy import LivePlanetPolicy
from games.balatro.strategy import COMMITTED, MATURE, BalatroStrategyTracker


class StrategyAwareLivePlanetPolicy(LivePlanetPolicy):
    """D7 preserves survival logic while using the universal strategy as hand intent."""

    def __init__(self, *args, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def _playstyle_fit(self, state, planet: object) -> tuple[float, bool]:
        hand_type = str(getattr(planet, "hand_type", ""))
        if not hand_type:
            resolution = self.strategy_tracker.observe(state)
            return 0.0, resolution.active_status in {COMMITTED, MATURE}
        fit, _ = self.strategy_tracker.hand_fit(state, hand_type)
        resolution = self.strategy_tracker.observe(state)
        return fit, resolution.active_status in {COMMITTED, MATURE}
