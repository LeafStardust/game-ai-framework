from __future__ import annotations

from dataclasses import dataclass, replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.build.profile import (
    BalatroBuildProfiler,
    BalatroPlaystyleIntentTracker,
    PlaystyleIntent,
)
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.joker import Playstyle
from games.balatro.live.hand_action_policy import LiveHandActionPolicy
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


_HAND_AXES = {
    Playstyle.HIGH_CARD.value,
    Playstyle.PAIR.value,
    Playstyle.TWO_PAIR.value,
    Playstyle.THREE_OF_A_KIND.value,
    Playstyle.STRAIGHT.value,
    Playstyle.FLUSH.value,
    Playstyle.FULL_HOUSE.value,
    Playstyle.FOUR_OF_A_KIND.value,
    Playstyle.FIVE_OF_A_KIND.value,
    Playstyle.FLUSH_HOUSE.value,
    Playstyle.FLUSH_FIVE.value,
}
_SUIT_AXES = {
    Playstyle.SPADES.value: "Spades",
    Playstyle.HEARTS.value: "Hearts",
    Playstyle.CLUBS.value: "Clubs",
    Playstyle.DIAMONDS.value: "Diamonds",
}
_FACE_RANKS = {"J", "Q", "K"}


@dataclass(frozen=True)
class HandPlaystyleWeights:
    """D1-only strength of build intent after tactical eligibility is established.

    These values never live on Joker definitions. Joker files continue to declare
    only directional affinities; D1 owns how much that direction matters while
    choosing among tactically acceptable hand actions.
    """

    recovery_gain: float = 12.0
    locked_conflict_multiplier: float = 1.5

    def __post_init__(self) -> None:
        if float(self.recovery_gain) < 0.0:
            raise ValueError("recovery_gain cannot be negative")
        if float(self.locked_conflict_multiplier) < 1.0:
            raise ValueError("locked_conflict_multiplier must be at least 1")


@dataclass(frozen=True)
class HandPlaystyleEvaluation:
    fit: float
    rank_fit: float
    recovery_value: float
    intent: PlaystyleIntent
    ante: int
    rationale: tuple[str, ...]


class LiveHandPlaystyleEvaluator:
    """Apply run-level playstyle intent to one currently legal D1 action.

    The signal is intentionally local to an already-generated legal action. It does
    not invent hidden draws, change clear probabilities, or alter Balatro scoring.
    The D1 hierarchy remains responsible for survival; this layer only distinguishes
    strategically coherent actions within that hierarchy and adds a bounded recovery
    preference when no current play reaches pace.
    """

    def __init__(
        self,
        *,
        base_evaluator: LiveHandDecisionEvaluator | None = None,
        profiler: BalatroBuildProfiler | None = None,
        intent_tracker: BalatroPlaystyleIntentTracker | None = None,
        weights: HandPlaystyleWeights | None = None,
    ) -> None:
        self.base_evaluator = base_evaluator or LiveHandDecisionEvaluator()
        self.profiler = profiler or BalatroBuildProfiler()
        self.intent_tracker = intent_tracker or BalatroPlaystyleIntentTracker()
        self.weights = weights or HandPlaystyleWeights()
        self.hand_evaluator = HandEvaluator()
        self._cached_state_id: int | None = None
        self._cached_evaluations: dict[tuple, HandPlaystyleEvaluation] = {}
        self._cached_intent: PlaystyleIntent | None = None
        self._cached_ante: int = 1

    @staticmethod
    def _exploratory_influence(ante: int) -> float:
        # Identical staging to D2: Ante 4 may exert full preference pressure while
        # still remaining completely pivotable. Irreversibility starts only at 5.
        if ante <= 1:
            return 0.25
        if ante == 2:
            return 0.50
        if ante == 3:
            return 0.75
        return 1.0

    def prepare(self, state) -> PlaystyleIntent:
        state_id = id(state)
        if self._cached_state_id == state_id and self._cached_intent is not None:
            return self._cached_intent

        profile = self.profiler.profile(state)
        intent = self.intent_tracker.resolve(profile)
        self._cached_state_id = state_id
        self._cached_evaluations = {}
        self._cached_intent = intent
        self._cached_ante = int(profile.ante)
        return intent

    def reset_cache(self) -> None:
        self._cached_state_id = None
        self._cached_evaluations = {}
        self._cached_intent = None
        self._cached_ante = 1

    def project_play(self, state, action):
        return self.base_evaluator.project_play(state, action)

    def evaluate(self, state, action) -> float:
        base = float(self.base_evaluator.evaluate(state, action))
        return base + self.evaluate_playstyle(state, action).recovery_value

    def evaluate_playstyle(
        self,
        state,
        action: BalatroAction,
    ) -> HandPlaystyleEvaluation:
        intent = self.prepare(state)
        signature = self._action_signature(action)
        cached = self._cached_evaluations.get(signature)
        if cached is not None:
            return cached

        fit, contributions = self._fit(action, intent)
        influence = (
            1.0
            if intent.locked
            else self._exploratory_influence(self._cached_ante)
        )
        rank_fit = fit * influence
        if intent.locked and rank_fit < 0.0:
            rank_fit *= self.weights.locked_conflict_multiplier

        recovery_value = rank_fit * self.weights.recovery_gain
        mode = "LOCKED" if intent.locked else "PIVOTABLE"
        intent_text = ",".join(
            f"{key}:{value:+.3f}"
            for key, value in intent.strengths
        ) or "NONE"
        rationale = (
            f"D1 playstyle fit={fit:.3f} rank_fit={rank_fit:.3f} mode={mode}",
            f"D1 playstyle intent={intent_text}",
            *contributions,
        )
        result = HandPlaystyleEvaluation(
            fit=fit,
            rank_fit=rank_fit,
            recovery_value=recovery_value,
            intent=intent,
            ante=self._cached_ante,
            rationale=rationale,
        )
        self._cached_evaluations[signature] = result
        return result

    @staticmethod
    def _action_signature(action: BalatroAction) -> tuple:
        return (
            str(action.name),
            tuple(
                (
                    str(getattr(card, "rank", "")),
                    str(getattr(card, "suit", "")),
                    id(card),
                )
                for card in action.cards
            ),
        )

    def _fit(
        self,
        action: BalatroAction,
        intent: PlaystyleIntent,
    ) -> tuple[float, tuple[str, ...]]:
        total = 0.0
        denominator = 0.0
        details: list[str] = []

        for key, raw_strength in intent.strengths:
            strength = max(-1.0, min(1.0, float(raw_strength)))
            signal = self._signal(action, str(key))
            if signal == 0.0:
                continue
            contribution = strength * signal
            total += contribution
            denominator += abs(strength)
            details.append(
                f"D1 axis {key}: strength={strength:+.3f} "
                f"signal={signal:+.3f} contribution={contribution:+.3f}"
            )

        fit = total / denominator if denominator > 0.0 else 0.0
        return fit, tuple(details)

    def _signal(self, action: BalatroAction, axis: str) -> float:
        cards = tuple(action.cards)
        card_count = max(1, len(cards))
        face_fraction = (
            sum(1 for card in cards if str(getattr(card, "rank", "")) in _FACE_RANKS)
            / card_count
        )

        if action.name == PLAY_CARDS:
            if axis in _HAND_AXES:
                hand = self.hand_evaluator.evaluate(list(cards)).value
                return 1.0 if hand == axis else 0.0
            if axis == Playstyle.FACE_CARDS.value:
                return face_fraction
            if axis == Playstyle.NO_FACE_CARDS.value:
                return 1.0 if face_fraction == 0.0 else 0.0
            if axis in _SUIT_AXES:
                suit = _SUIT_AXES[axis]
                return (
                    sum(1 for card in cards if str(getattr(card, "suit", "")) == suit)
                    / card_count
                )
            if axis == Playstyle.NO_DISCARD.value:
                return 1.0
            return 0.0

        if action.name == DISCARD_CARDS:
            # Discarding a face card supports NO_FACE and conflicts with FACE; the
            # signed intent usually contains both sides for explicit conflicts such
            # as Ride the Bus versus Business Card, so this becomes a strong but
            # still bounded signal to throw away or retain those cards.
            if axis == Playstyle.FACE_CARDS.value:
                return -face_fraction
            if axis == Playstyle.NO_FACE_CARDS.value:
                return face_fraction
            if axis in _SUIT_AXES:
                suit = _SUIT_AXES[axis]
                return -(
                    sum(1 for card in cards if str(getattr(card, "suit", "")) == suit)
                    / card_count
                )
            if axis == Playstyle.DISCARD.value:
                return 1.0
            if axis == Playstyle.NO_DISCARD.value:
                return -1.0
            return 0.0

        return 0.0


class BuildAwareLiveHandActionPolicy(LiveHandActionPolicy):
    """D1 policy with build intent inside, never above, the survival hierarchy.

    Clear probability and exactness remain the first two ranking dimensions. Once
    those are equal, playstyle fit is considered before progress/resource tie-breaks.
    Pace-play candidates are treated the same way after they have already met the
    pace floor. PACE_RECOVERY receives only the bounded ``recovery_gain`` adjustment.
    """

    def __init__(
        self,
        thresholds=None,
        *,
        evaluator: LiveHandDecisionEvaluator | None = None,
        profiler: BalatroBuildProfiler | None = None,
        intent_tracker: BalatroPlaystyleIntentTracker | None = None,
        weights: HandPlaystyleWeights | None = None,
    ) -> None:
        self.playstyle_evaluator = LiveHandPlaystyleEvaluator(
            base_evaluator=evaluator,
            profiler=profiler,
            intent_tracker=intent_tracker,
            weights=weights,
        )
        self._ranking_state = None
        super().__init__(thresholds, evaluator=self.playstyle_evaluator)

    def decide(self, state, plans, **kwargs):
        self._ranking_state = state
        self.playstyle_evaluator.prepare(state)
        try:
            decision = super().decide(state, plans, **kwargs)
            playstyle = self.playstyle_evaluator.evaluate_playstyle(
                state,
                decision.action,
            )
            return replace(
                decision,
                rationale=decision.rationale + playstyle.rationale,
            )
        finally:
            self._ranking_state = None
            self.playstyle_evaluator.reset_cache()

    def _within_type_key(self, plan):
        base = super()._within_type_key(plan)
        if self._ranking_state is None:
            return base
        fit = self.playstyle_evaluator.evaluate_playstyle(
            self._ranking_state,
            plan.action,
        ).rank_fit
        return (base[0], base[1], fit, *base[2:])

    def _pace_play_key(self, plan, pace_ratio: float):
        base = super()._pace_play_key(plan, pace_ratio)
        if self._ranking_state is None:
            return base
        fit = self.playstyle_evaluator.evaluate_playstyle(
            self._ranking_state,
            plan.action,
        ).rank_fit
        return (base[0], base[1], fit, *base[2:])
