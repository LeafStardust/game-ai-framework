from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.actions import SELL_JOKER, SKIP_BOOSTER, BalatroAction
from games.balatro.build import ContextualConsumableTargetEvaluator, JokerBuildTransitionPlanner
from games.balatro.discovery import is_undiscovered
from games.balatro.joker_policy import BUY, REPLACE
from games.balatro.live.consumable_timing_core import ConsumableTargetThresholds
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


@dataclass(frozen=True)
class PackChoiceThresholds:
    """Thresholds owned only by D9 visible booster-pack choice."""

    skip_bias: float = 0.0

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object] | None,
    ) -> "PackChoiceThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D9 pack-choice threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})


class PlaybookPackTargetEvaluator:
    """Apply D10 admission to the same B6 target ranking used by D6.

    The underlying deterministic target evaluator remains the single source of
    target quality. D10 only adds a pack-specific admission threshold using the
    existing ``ConsumableTargetThresholds`` contract; it does not create another
    target-value scale.
    """

    def __init__(
        self,
        *,
        evaluator=None,
        thresholds: ConsumableTargetThresholds | None = None,
    ) -> None:
        self.evaluator = evaluator or ContextualConsumableTargetEvaluator()
        self.thresholds = thresholds

    def _thresholds_for_state(self, state) -> ConsumableTargetThresholds:
        if self.thresholds is not None:
            return self.thresholds
        try:
            block = default_balatro_playbooks().for_state(state).thresholds_for("D10")
        except BalatroPlaybookNotFound:
            block = {}
        return ConsumableTargetThresholds.from_mapping(block)

    def recommend(self, state, consumable):
        evaluation = self.evaluator.recommend(state, consumable)
        if evaluation is None:
            return None
        if not self._thresholds_for_state(state).accepts(evaluation):
            return None
        return evaluation


class PlaybookBalatroPackPolicy(BalatroPackPolicy):
    """D9/D10 cartridge adapter over the existing pack mechanics policy.

    Explicit constructor thresholds remain authoritative for tests/tools. Otherwise
    the observed deck/stake selects D9 skip bias and D10 target admission on every
    decision, so a future cartridge can retune pack behavior without replacing the
    shared pack implementation.

    Stochastic consumables whose public outcome pools are not yet modeled remain
    delegated to the shared fail-closed pack policy; the cartridge does not assign
    synthetic option values to unresolved random outcomes.
    """

    def __init__(
        self,
        *,
        skip_bias: float | None = None,
        target_thresholds: ConsumableTargetThresholds | None = None,
        consumable_target_evaluator=None,
        **kwargs,
    ) -> None:
        self._skip_bias_override = (
            None if skip_bias is None else float(skip_bias)
        )
        wrapped_target_evaluator = PlaybookPackTargetEvaluator(
            evaluator=consumable_target_evaluator,
            thresholds=target_thresholds,
        )
        super().__init__(
            skip_bias=0.0 if skip_bias is None else float(skip_bias),
            consumable_target_evaluator=wrapped_target_evaluator,
            **kwargs,
        )
        self._pack_joker_factory = LiveJokerFactory()

    def skip_bias_for_state(self, state) -> float:
        if self._skip_bias_override is not None:
            return self._skip_bias_override
        try:
            block = default_balatro_playbooks().for_state(state).thresholds_for("D9")
        except BalatroPlaybookNotFound:
            block = {}
        return float(PackChoiceThresholds.from_mapping(block).skip_bias)

    def rank_actions(self, state, actions):
        ranked = super().rank_actions(state, actions)
        return sorted(
            ranked,
            key=lambda result: (
                result.total,
                result.action.name != SKIP_BOOSTER,
                is_undiscovered(getattr(result.action, "target", None)),
            ),
            reverse=True,
        )

    def _buffoon_joker_score(self, state, action, choice):
        """Delegate visible Buffoon Jokers to canonical D2 acquisition authority.

        Booster cost is already sunk when D9 runs, so the projected Joker must be
        evaluated at zero acquisition price. Joker-slot and replacement opportunity
        costs remain part of D2 exactly as they are for every other acquisition path.
        """
        if str(getattr(state, "phase", "")) != "BUFFOON_PACK":
            return None
        if getattr(choice, "kind", None) != "JOKER":
            return None

        data = getattr(choice, "data", None)
        if not isinstance(data, dict):
            return PackActionScore(
                action,
                -1.0,
                ("visible Buffoon Joker cannot be modeled by canonical D2",),
            )

        # Never mutate the live pack observation. A Buffoon selection is free because
        # the booster has already been paid for, even if Balatro exposes the Joker's
        # ordinary shop cost in the visible card metadata.
        pack_data = dict(data)
        pack_data["cost"] = 0
        candidate = self._pack_joker_factory.create(pack_data)
        evaluator = getattr(self.item_estimator, "joker_build_value", None)
        if candidate is None or evaluator is None:
            return PackActionScore(
                action,
                -1.0,
                ("visible Buffoon Joker canonical D2 evaluator unavailable",),
            )

        policy = PlaybookJokerAcquisitionPolicy(
            JokerBuildTransitionPlanner(evaluator=evaluator),
        )
        decision = policy.decide(state, candidate)
        selected = decision.selected

        if decision.action == BUY and selected is not None:
            return PackActionScore(
                action,
                float(selected.total_advantage),
                (
                    f"visible Buffoon Joker cleared canonical D2 acquisition: {decision.candidate}",
                    "opened-pack Joker acquisition cost normalized to $0",
                    *decision.rationale,
                    *selected.rationale,
                ),
            )

        if (
            decision.action == REPLACE
            and selected is not None
            and selected.replace_index is not None
        ):
            # Pack replacement is deliberately two checkpoints. Sell only after the
            # pack is open and a concrete visible Joker has cleared D2. The next pack
            # observation then sees the free slot and may select the Joker normally.
            sell = BalatroAction(SELL_JOKER, target=int(selected.replace_index))
            return PackActionScore(
                sell,
                float(selected.total_advantage),
                (
                    f"visible Buffoon Joker selected for replacement: {decision.candidate}",
                    "opened-pack Joker acquisition cost normalized to $0",
                    f"sell incumbent slot {selected.replace_index} only after pack reveal",
                    "re-observe the same Buffoon pack after the sale, then take the selected Joker",
                    *decision.rationale,
                    *selected.rationale,
                ),
            )

        return PackActionScore(
            action,
            -1.0,
            (
                "visible Buffoon Joker does not clear canonical D2 acquisition",
                *decision.rationale,
            ),
        )

    def score_action(self, state, action):
        if action.name == SKIP_BOOSTER:
            bias = self.skip_bias_for_state(state)
            return PackActionScore(
                action,
                bias,
                (f"skip booster; D9 skip_bias={bias:.3f}",),
            )

        choice = getattr(action, "target", None)
        buffoon_joker = self._buffoon_joker_score(state, action, choice)
        if buffoon_joker is not None:
            return buffoon_joker

        return super().score_action(state, action)
