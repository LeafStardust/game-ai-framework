from __future__ import annotations

from dataclasses import dataclass, replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.build.playing_card_synergy import (
    ContextualPlayingCardSynergyEvaluator,
)
from games.balatro.build.profile import BalatroBuildProfiler, BuildProfile
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.hand_action_policy import LiveHandActionPolicy
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


_FACE_RANKS = frozenset({"J", "Q", "K"})


@dataclass(frozen=True)
class HeldCardPreservationWeights:
    """Bounded D1 value for resources deliberately left in hand."""

    steel: float = 18.0
    blue_seal: float = 12.0
    build_interaction: float = 8.0

    def __post_init__(self) -> None:
        if float(self.steel) < 0.0:
            raise ValueError("steel preservation weight cannot be negative")
        if float(self.blue_seal) < 0.0:
            raise ValueError("blue_seal preservation weight cannot be negative")
        if float(self.build_interaction) < 0.0:
            raise ValueError("build_interaction preservation weight cannot be negative")


@dataclass(frozen=True)
class HeldCardPreservationEvaluation:
    value: float
    steel_cards: int
    blue_seals: int
    build_gain: float
    rationale: tuple[str, ...]


class LiveHandBuildEvaluator:
    """Preserve public held-card resources beneath D1 survival authority.

    Canonical Bond/composition shaping is supplied by
    ``StrategyAwareLiveHandActionPolicy``. This evaluator intentionally contains no
    categorical intent vector, Ante lock, or independent strategy authority.
    """

    def __init__(
        self,
        *,
        base_evaluator: LiveHandDecisionEvaluator | None = None,
        profiler: BalatroBuildProfiler | None = None,
        preservation_weights: HeldCardPreservationWeights | None = None,
    ) -> None:
        self.base_evaluator = base_evaluator or LiveHandDecisionEvaluator()
        self.profiler = profiler or BalatroBuildProfiler()
        self.preservation_weights = preservation_weights or HeldCardPreservationWeights()
        self.playing_card_synergy = ContextualPlayingCardSynergyEvaluator(
            profiler=self.profiler,
        )
        self._cached_state_id: int | None = None
        self._cached_preservation: dict[tuple, HeldCardPreservationEvaluation] = {}
        self._cached_profile: BuildProfile | None = None
        self._cached_card_preservation: dict[int, tuple[float, float]] = {}

    def prepare(self, state) -> BuildProfile:
        state_id = id(state)
        if self._cached_state_id == state_id and self._cached_profile is not None:
            return self._cached_profile

        profile = self.profiler.profile(state)
        self._cached_state_id = state_id
        self._cached_preservation = {}
        self._cached_profile = profile
        self._cached_card_preservation = self._card_preservation_values(state, profile)
        return profile

    def reset_cache(self) -> None:
        self._cached_state_id = None
        self._cached_preservation = {}
        self._cached_profile = None
        self._cached_card_preservation = {}

    def project_play(self, state, action):
        return self.base_evaluator.project_play(state, action)

    def evaluate(self, state, action) -> float:
        base = float(self.base_evaluator.evaluate(state, action))
        return base + self.evaluate_preservation(state, action).value

    def evaluate_preservation(
        self,
        state,
        action: BalatroAction,
    ) -> HeldCardPreservationEvaluation:
        self.prepare(state)
        signature = self._action_signature(action)
        cached = self._cached_preservation.get(signature)
        if cached is not None:
            return cached

        if action.name not in {PLAY_CARDS, DISCARD_CARDS}:
            result = HeldCardPreservationEvaluation(0.0, 0, 0, 0.0, ())
            self._cached_preservation[signature] = result
            return result

        removed_ids = {id(card) for card in action.cards}
        kept_cards = [
            card
            for card in getattr(state, "hand", [])
            if id(card) not in removed_ids
        ]
        steel_cards = sum(
            1
            for card in kept_cards
            if not bool(getattr(card, "debuffed", False))
            and getattr(card, "enhancement", None) == "Steel"
        )
        blue_seals = sum(
            1
            for card in kept_cards
            if not bool(getattr(card, "debuffed", False))
            and getattr(card, "seal", None) == "Blue"
        )
        build_gain = sum(
            self._cached_card_preservation.get(id(card), (0.0, 0.0))[1]
            for card in kept_cards
        )
        value = sum(
            self._cached_card_preservation.get(id(card), (0.0, 0.0))[0]
            for card in kept_cards
        )
        result = HeldCardPreservationEvaluation(
            value=value,
            steel_cards=steel_cards,
            blue_seals=blue_seals,
            build_gain=build_gain,
            rationale=(
                f"D1 retained-card value={value:.3f} steel={steel_cards} "
                f"blue_seal={blue_seals} build_gain={build_gain:.3f}",
            ),
        )
        self._cached_preservation[signature] = result
        return result

    def _card_preservation_values(
        self,
        state,
        profile: BuildProfile,
    ) -> dict[int, tuple[float, float]]:
        values: dict[int, tuple[float, float]] = {}
        for card in getattr(state, "hand", []):
            active = not bool(getattr(card, "debuffed", False))
            direct = 0.0
            if active and getattr(card, "enhancement", None) == "Steel":
                direct += float(self.preservation_weights.steel)
            if active and getattr(card, "seal", None) == "Blue":
                direct += float(self.preservation_weights.blue_seal)

            build_gain = float(
                self.playing_card_synergy.evaluate(
                    state,
                    rank=getattr(card, "rank", None),
                    suit=getattr(card, "suit", None),
                    enhancement=getattr(card, "enhancement", None),
                    seal=getattr(card, "seal", None),
                    edition=getattr(card, "edition", None),
                    profile=profile,
                ).total_gain
            )
            total = direct + build_gain * float(
                self.preservation_weights.build_interaction
            )
            values[id(card)] = (total, build_gain)
        return values

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


class BuildAwareLiveHandActionPolicy(LiveHandActionPolicy):
    """D1 policy with held-resource preservation beneath survival hierarchy."""

    def __init__(
        self,
        thresholds=None,
        *,
        evaluator: LiveHandDecisionEvaluator | None = None,
        profiler: BalatroBuildProfiler | None = None,
        preservation_weights: HeldCardPreservationWeights | None = None,
    ) -> None:
        self.build_evaluator = LiveHandBuildEvaluator(
            base_evaluator=evaluator,
            profiler=profiler,
            preservation_weights=preservation_weights,
        )
        self._ranking_state = None
        self._hand_evaluator = HandEvaluator()
        super().__init__(thresholds, evaluator=self.build_evaluator)

    def decide(self, state, plans, **kwargs):
        self._ranking_state = state
        self.build_evaluator.prepare(state)
        try:
            decision = super().decide(state, plans, **kwargs)
            preservation = self.build_evaluator.evaluate_preservation(
                state,
                decision.action,
            )
            return replace(
                decision,
                rationale=decision.rationale + preservation.rationale,
            )
        finally:
            self._ranking_state = None
            self.build_evaluator.reset_cache()

    def _preservation(self, plan) -> float:
        if self._ranking_state is None:
            return 0.0
        return self.build_evaluator.evaluate_preservation(
            self._ranking_state,
            plan.action,
        ).value

    def _ride_bus_terminal_preservation(self, plan) -> int:
        """Prefer not resetting an accumulated Bus stack on equivalent clears.

        This key is consulted only by ``_safe_equivalent_clear_key`` after exactness,
        remaining hands/discards, clear probability, and progress have already tied.
        Non-terminal D1 choices therefore continue to rely on the planner's literal
        state projection rather than a local Ride the Bus bonus.
        """
        state = self._ranking_state
        if state is None or plan.action.name != PLAY_CARDS:
            return 0

        stack = max(
            (
                max(0, int(getattr(joker, "mult", 0) or 0))
                for joker in tuple(getattr(state, "jokers", ()) or ())
                if type(joker).__name__ == "RideTheBusJoker"
                and not bool(getattr(joker, "debuffed", False))
            ),
            default=0,
        )
        if stack <= 0:
            return 0

        cards = list(getattr(plan.action, "cards", ()) or ())
        if not cards:
            return 1
        rules = hand_rules_for_state(state)
        hand = self._hand_evaluator.evaluate(cards, rules=rules)
        scoring = self._hand_evaluator.scoring_cards(hand, cards, rules=rules)
        resets = any(
            str(getattr(card, "rank", "") or "") in _FACE_RANKS
            for card in scoring
        )
        return 0 if resets else 1

    def _within_type_key(self, plan):
        base = super()._within_type_key(plan)
        # Base authority: clear probability, exactness, progress, hands, discards,
        # score. Held-resource preservation is a secondary choice only after all
        # full-blind survival/progress/resource dimensions have tied.
        return (*base[:-1], self._preservation(plan), base[-1])

    def _safe_equivalent_clear_key(self, plan):
        base = super()._safe_equivalent_clear_key(plan)
        # Exactness, remaining hands/discards, clear probability and progress all
        # remain above Ride the Bus / held-resource preservation. Preserve an active
        # Bus stack only before the final overkill/expected-score tie-break.
        return (
            *base[:-1],
            self._ride_bus_terminal_preservation(plan),
            self._preservation(plan),
            base[-1],
        )

    def _pace_play_key(self, plan, pace_ratio: float):
        base = super()._pace_play_key(plan, pace_ratio)
        # Pace-qualified candidates still compare full-blind survival/progress and
        # remaining round resources first. Preservation may break only the final
        # local pace-closeness tie.
        return (*base[:-1], self._preservation(plan), base[-1])
