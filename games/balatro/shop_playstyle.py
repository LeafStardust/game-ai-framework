from __future__ import annotations

from games.balatro.actions import BUY_CONSUMABLE
from games.balatro.consumable import PlanetCard
from games.balatro.shop_policy import DefaultShopItemValueEstimator


class BuildAwareShopItemValueEstimator(DefaultShopItemValueEstimator):
    """D14 item value with bounded B3 intent for explicit Planet hand targets.

    The inherited estimator already owns the shared ``JokerBuildValueEvaluator``.
    Reusing that evaluator's profiler and run-scoped intent tracker keeps D14 on the
    same Ante-5 commitment as D1/D2/D7/D9. Only Planets receive this direct bonus:
    their target poker hand is public and explicit, so no consumable-name strategy
    table or hidden outcome inference is required.
    """

    @staticmethod
    def _exploratory_influence(ante: int) -> float:
        if ante <= 1:
            return 0.25
        if ante == 2:
            return 0.50
        if ante == 3:
            return 0.75
        return 1.0

    def _planet_playstyle_value(self, state, planet) -> tuple[float, float, bool]:
        profile = self.joker_build_value.profiler.profile(state)
        intent = self.joker_build_value.intent_tracker.resolve(profile)
        hand_type = str(getattr(planet, "hand_type", ""))
        if not hand_type:
            return 0.0, 0.0, intent.locked

        fit = max(-1.0, min(1.0, float(intent.strength(hand_type))))
        influence = (
            1.0
            if intent.locked
            else self._exploratory_influence(int(profile.ante))
        )
        value = fit * influence
        return fit, value, intent.locked

    def estimate(self, state, action):
        base_value, notes = super().estimate(state, action)
        target = getattr(action, "target", None)
        category = str(getattr(target, "category", "")).upper()
        if action.name != BUY_CONSUMABLE or not (
            isinstance(target, PlanetCard) or category == "PLANET"
        ):
            return base_value, notes

        fit, value, locked = self._planet_playstyle_value(state, target)
        mode = "LOCKED" if locked else "PIVOTABLE"
        return (
            base_value + value,
            notes
            + (
                f"B3 Planet playstyle fit={fit:.3f} value={value:.3f} mode={mode}",
            ),
        )
