from __future__ import annotations

import copy
from dataclasses import dataclass

from games.balatro.build.joker_semantics import (
    CONSUMABLE_DUPLICATE,
    SemanticJokerBehaviorAnalyzer,
)
from games.balatro.build.profile import (
    BalatroBuildProfiler,
    BalatroPlaystyleIntentTracker,
)
from games.balatro.consumable import ConsumableContext
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator, LivePlayProjection
from games.balatro.planet_outlook import PlanetOutlookEvaluator
from games.balatro.planet_scaler_authority import has_planet_use_scaler


USE = "USE"
HOLD = "HOLD"


@dataclass(frozen=True)
class PlanetPolicyThresholds:
    clear_probability_epsilon: float = 1e-12
    immediate_score_epsilon: float = 1e-12
    duplicate_hold_minimum: float = 1.0


@dataclass(frozen=True)
class PlanetDecision:
    decision: str
    planet: object
    before_projection: LivePlayProjection | None
    after_projection: LivePlayProjection | None
    required_per_hand: float
    immediate_score_gain: float
    clear_probability_gain: float
    duplicate_hold_value: float
    level_gain: int
    observed_hand_plays: int
    rationale: tuple[str, ...] = ()
    playstyle_fit: float = 0.0
    playstyle_locked: bool = False
    structural_feasibility: float = 0.0
    expected_future_frequency: float = 0.0
    marginal_level_gain: float = 0.0
    future_value: float = 0.0

    @property
    def should_use(self) -> bool:
        return self.decision == USE


class LivePlanetPolicy:
    """D7 Planet selection and USE-versus-HOLD policy from public state only."""

    def __init__(
        self,
        *,
        thresholds=None,
        hand_evaluator=None,
        joker_analyzer=None,
        profiler=None,
        intent_tracker=None,
        planet_outlook=None,
    ) -> None:
        self.thresholds = thresholds or PlanetPolicyThresholds()
        self.hand_evaluator = hand_evaluator or LiveHandDecisionEvaluator()
        self.joker_analyzer = joker_analyzer or SemanticJokerBehaviorAnalyzer()
        self.profiler = profiler or BalatroBuildProfiler()
        self.intent_tracker = intent_tracker or BalatroPlaystyleIntentTracker()
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

    def _playstyle_fit(self, state, planet: object) -> tuple[float, bool]:
        profile = self.profiler.profile(state)
        intent = self.intent_tracker.resolve(profile)
        hand_type = str(getattr(planet, "hand_type", ""))
        if not hand_type:
            return 0.0, intent.locked
        strength = max(-1.0, min(1.0, float(intent.strength(hand_type))))
        influence = 1.0 if intent.locked else self._exploratory_influence(int(profile.ante))
        return strength * influence, intent.locked

    def recommend(self, state, planet: object) -> PlanetDecision:
        required = self._required_per_hand(state)
        if getattr(state, "phase", None) != "SELECTING_HAND":
            return self._hold(planet, required, "D7 Planet timing currently requires SELECTING_HAND")
        if str(getattr(planet, "category", "")).upper() != "PLANET":
            return self._hold(planet, required, "candidate is not a Planet")
        planet_index = self._identity_index(getattr(state, "consumables", ()), planet)
        if planet_index is None:
            return self._hold(planet, required, "candidate Planet is not held")

        # A Planet-use scaler makes consumption itself a deterministic permanent
        # engine upgrade. Resolve that mechanic before score projection: incomplete
        # Joker projections and duplicate/slot timing must not suppress guaranteed
        # scaler growth, and this avoids an unnecessary full visible-hand projection.
        if has_planet_use_scaler(state):
            transformed = self._simulate_use(state, planet_index)
            if transformed is None:
                return self._hold(planet, required, "Planet failed deterministic copied simulation")
            hand_type = str(getattr(planet, "hand_type", ""))
            before_level = int((getattr(state, "hand_levels", {}) or {}).get(hand_type, 0))
            after_level = int((getattr(transformed, "hand_levels", {}) or {}).get(hand_type, 0))
            level_gain = after_level - before_level
            observed_plays = int((getattr(state, "hand_play_counts", {}) or {}).get(hand_type, 0) or 0)
            if level_gain <= 0:
                return self._hold(planet, required, "Planet produced no permanent hand-level gain")
            return PlanetDecision(
                decision=USE,
                planet=planet,
                before_projection=None,
                after_projection=None,
                required_per_hand=required,
                immediate_score_gain=0.0,
                clear_probability_gain=0.0,
                duplicate_hold_value=self._duplicate_hold_value(state),
                level_gain=level_gain,
                observed_hand_plays=observed_plays,
                rationale=(
                    "USE: active Planet-use scaler makes consumption guaranteed permanent engine growth",
                    f"Planet={getattr(planet, 'name', 'Planet')} hand={hand_type} level {before_level} -> {after_level}",
                    "Planet-scaler authority precedes ordinary projection, duplication, and slot-timing preferences",
                ),
            )

        before = self._best_play_projection(state)
        if before is None:
            return self._hold(planet, required, "no legal visible play")
        if not before.joker_projection_complete:
            return self._hold(planet, required, "current build has unsupported Joker score projection", before=before)

        transformed = self._simulate_use(state, planet_index)
        if transformed is None:
            return self._hold(planet, required, "Planet failed deterministic copied simulation", before=before)
        after = self._best_play_projection(transformed)
        if after is None:
            return self._hold(planet, required, "Planet use leaves no legal visible play", before=before)
        if not after.joker_projection_complete:
            return self._hold(planet, required, "Planet-upgraded build has unsupported Joker score projection", before=before, after=after)

        hand_type = str(getattr(planet, "hand_type", ""))
        before_level = int((getattr(state, "hand_levels", {}) or {}).get(hand_type, 0))
        after_level = int((getattr(transformed, "hand_levels", {}) or {}).get(hand_type, 0))
        level_gain = after_level - before_level
        score_gain = float(after.expected_hand_score - before.expected_hand_score)
        clear_gain = float(after.clear_probability - before.clear_probability)
        observed_plays = int((getattr(state, "hand_play_counts", {}) or {}).get(hand_type, 0) or 0)
        duplicate_hold_value = self._duplicate_hold_value(state)
        slots_full = self._consumable_slots_full(state)
        playstyle_fit, playstyle_locked = self._playstyle_fit(state, planet)
        outlook = self.planet_outlook.evaluate(state, planet)

        if level_gain <= 0:
            decision, reason = HOLD, "Planet produced no permanent hand-level gain"
        elif clear_gain > self.thresholds.clear_probability_epsilon:
            decision, reason = USE, "Planet upgrade increases blind-clear probability"
        elif before.expected_hand_score + self.thresholds.immediate_score_epsilon < required <= after.expected_hand_score + self.thresholds.immediate_score_epsilon:
            decision, reason = USE, "Planet upgrade restores required blind pace"
        elif max(0, int(getattr(state, "hands_remaining", 0))) <= 1 and score_gain > self.thresholds.immediate_score_epsilon:
            decision, reason = USE, "final hand gains score from deterministic Planet upgrade"
        elif slots_full:
            decision, reason = USE, "full consumable slots favor realizing the permanent Planet upgrade"
        elif duplicate_hold_value >= self.thresholds.duplicate_hold_minimum:
            decision, reason = HOLD, "observable consumable-duplication value makes preserving this Planet strategically positive"
        else:
            decision, reason = USE, "permanent Planet upgrade has no modeled positive hold advantage"

        mode = "LOCKED" if playstyle_locked else "PIVOTABLE"
        return PlanetDecision(
            decision=decision,
            planet=planet,
            before_projection=before,
            after_projection=after,
            required_per_hand=required,
            immediate_score_gain=score_gain,
            clear_probability_gain=clear_gain,
            duplicate_hold_value=duplicate_hold_value,
            level_gain=level_gain,
            observed_hand_plays=observed_plays,
            rationale=(
                f"{decision}: {reason}",
                f"Planet={getattr(planet, 'name', 'Planet')} hand={hand_type} level {before_level} -> {after_level}",
                f"best-play clear probability {before.clear_probability:.6f} -> {after.clear_probability:.6f}",
                f"best-play expected score {before.expected_hand_score:.3f} -> {after.expected_hand_score:.3f}",
                f"required pace per remaining hand={required:.3f}",
                f"observed hand plays={observed_plays}",
                f"Planet structural feasibility={outlook.structural_feasibility:.6f}",
                f"Planet expected future frequency={outlook.expected_future_frequency:.6f}",
                f"Planet marginal level gain={outlook.marginal_level_gain:.3f}",
                f"Planet future value={outlook.future_value:.6f}",
                f"Planet speculative={outlook.speculative}",
                f"consumable duplicate hold value={duplicate_hold_value:.3f}",
                f"duplicate hold threshold={self.thresholds.duplicate_hold_minimum:.3f}",
                f"consumable slots full={slots_full}",
                f"D7 playstyle fit={playstyle_fit:.3f} mode={mode}",
            ),
            playstyle_fit=playstyle_fit,
            playstyle_locked=playstyle_locked,
            structural_feasibility=outlook.structural_feasibility,
            expected_future_frequency=outlook.expected_future_frequency,
            marginal_level_gain=outlook.marginal_level_gain,
            future_value=outlook.future_value,
        )

    def recommend_inventory(self, state) -> tuple[PlanetDecision, ...]:
        decisions = [
            self.recommend(state, item)
            for item in getattr(state, "consumables", ())
            if str(getattr(item, "category", "")).upper() == "PLANET"
        ]
        return tuple(sorted(decisions, key=self._decision_key, reverse=True))

    def _duplicate_hold_value(self, state) -> float:
        value = 0.0
        for joker in getattr(state, "jokers", ()):
            descriptor = self.joker_analyzer.describe(joker)
            if CONSUMABLE_DUPLICATE not in descriptor.produces:
                continue
            magnitude = getattr(descriptor, "feature_magnitude", None)
            amount = float(magnitude(CONSUMABLE_DUPLICATE)) if callable(magnitude) else 1.0
            value = max(value, amount)
        return value

    def _simulate_use(self, state, planet_index: int):
        simulated = copy.deepcopy(state)
        if not (0 <= planet_index < len(simulated.consumables)):
            return None
        planet = simulated.consumables[planet_index]
        context = ConsumableContext(state=simulated)
        if not planet.can_use(context):
            return None
        planet.use(context)
        simulated.consumables.pop(planet_index)
        return simulated

    def _best_play_projection(self, state) -> LivePlayProjection | None:
        best = None
        for action in self.hand_evaluator.action_generator.generate_play_actions(state):
            projection = self.hand_evaluator.project_play(state, action)
            if best is None or self._projection_key(projection) > self._projection_key(best):
                best = projection
        return best

    @staticmethod
    def _projection_key(projection: LivePlayProjection) -> tuple[float, ...]:
        return (
            float(projection.clear_probability),
            float(projection.expected_hand_score),
            float(projection.hand_score),
            float(projection.maximum_hand_score),
        )

    @staticmethod
    def _identity_index(items, candidate: object) -> int | None:
        for index, item in enumerate(items):
            if item is candidate:
                return index
        return None

    @staticmethod
    def _required_per_hand(state) -> float:
        requirement = int(getattr(getattr(state, "blind", None), "requirement", 0))
        remaining = max(0.0, float(requirement - int(getattr(state, "score", 0))))
        return remaining / max(1, int(getattr(state, "hands_remaining", 1)))

    @staticmethod
    def _consumable_slots_full(state) -> bool:
        slots = max(0, int(getattr(state, "consumable_slots", 0)))
        return slots > 0 and len(getattr(state, "consumables", ())) >= slots

    @staticmethod
    def _decision_key(decision: PlanetDecision) -> tuple:
        return (
            1 if decision.should_use else 0,
            float(decision.clear_probability_gain),
            float(decision.immediate_score_gain),
            float(decision.future_value),
            float(decision.playstyle_fit),
            int(decision.observed_hand_plays),
            int(decision.level_gain),
            str(getattr(decision.planet, "name", "")),
        )

    @staticmethod
    def _hold(planet, required_per_hand, reason, *, before=None, after=None) -> PlanetDecision:
        return PlanetDecision(
            HOLD,
            planet,
            before,
            after,
            required_per_hand,
            0.0,
            0.0,
            0.0,
            0,
            0,
            (f"HOLD: {reason}",),
        )
