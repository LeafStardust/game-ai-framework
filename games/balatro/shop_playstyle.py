from __future__ import annotations

from games.balatro.actions import BUY_CONSUMABLE
from games.balatro.consumable import PlanetCard
from games.balatro.planet_outlook import PlanetOutlookEvaluator
from games.balatro.shop_policy import DefaultShopItemValueEstimator


class BuildAwareShopItemValueEstimator(DefaultShopItemValueEstimator):
    """D14 item value with shared B3 intent and public Planet future outlook.

    Joker valuation continues to use the inherited shared B3 evaluator. Planet
    acquisition additionally asks whether the target hand is structurally feasible
    in the unordered owned deck and how often public run history says that hand is
    actually being played. This prevents a large raw level increment from making an
    unsupported speculative Planet attractive by itself.
    """

    def __init__(self, *args, planet_outlook=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.planet_outlook = planet_outlook or PlanetOutlookEvaluator()

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
        target = getattr(action, "target", None)
        category = str(getattr(target, "category", "")).upper()
        if action.name != BUY_CONSUMABLE or not (
            isinstance(target, PlanetCard) or category == "PLANET"
        ):
            return super().estimate(state, action)

        outlook = self.planet_outlook.evaluate(state, target)
        # Acquisition utility is intentionally frequency-gated. A Planet still has
        # a small permanent-upgrade floor, but most of its value must come from a
        # hand the current public run is plausibly going to play again.
        base_value = 0.75 + min(5.25, 5.0 * float(outlook.future_value))
        contextual = self.consumable_build.evaluate(target, state)
        base_value, notes = self._with_consumable_build_path(
            base_value,
            (
                f"Planet future frequency={outlook.expected_future_frequency:.6f}",
                f"Planet structural feasibility={outlook.structural_feasibility:.6f}",
                f"Planet observed plays={outlook.observed_plays}/{outlook.total_observed_plays}",
                f"Planet marginal level gain={outlook.marginal_level_gain:.3f}",
                f"Planet future value={outlook.future_value:.6f}",
                f"Planet speculative={outlook.speculative}",
            ),
            contextual,
        )

        fit, value, locked = self._planet_playstyle_value(state, target)
        mode = "LOCKED" if locked else "PIVOTABLE"
        return (
            base_value + value,
            notes
            + (
                f"B3 Planet playstyle fit={fit:.3f} value={value:.3f} mode={mode}",
            ),
        )
