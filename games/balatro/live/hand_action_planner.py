from __future__ import annotations

from games.balatro.actions import BalatroAction, USE_CONSUMABLE
from games.balatro.blinds.blind import BlindType
from games.balatro.live.blind_clear_planner import LiveBlindPlanValue, _ActionEstimate
from games.balatro.live.consumable_timing import LiveConsumableTimingPolicy
from games.balatro.live.hand_action_planner_core import (
    D1LiveBlindClearPlanner as _CoreD1LiveBlindClearPlanner,
)


class D1LiveBlindClearPlanner(_CoreD1LiveBlindClearPlanner):
    """D1 planner with conservative deterministic consumable clear integration.

    The existing Play/Discard search remains unchanged. At the authoritative root
    only, D1 may additionally consider one supported held consumable when the B6
    timing model proves that its deterministic transformation changes the current
    best visible play from non-guaranteed to a guaranteed immediate blind clear.

    The consumable itself spends no hand or discard. Its plan value therefore
    represents the already-proven next Play after the transformation, while real
    execution still performs only USE_CONSUMABLE and then re-observes/replans.
    Boss-blind consumable integration remains deliberately excluded until the
    generalized boss-mechanics item is completed.
    """

    def __init__(
        self,
        *args,
        consumable_timing_policy: LiveConsumableTimingPolicy | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.consumable_timing_policy = (
            consumable_timing_policy
            or LiveConsumableTimingPolicy(
                hand_evaluator=self.evaluator,
                defer_blind_clear_to_d1=False,
            )
        )
        self._integrated_consumable_estimates: dict[int, _ActionEstimate] = {}

    def reset_search_stats(self) -> None:
        super().reset_search_stats()
        self._integrated_consumable_estimates.clear()

    def _candidate_actions(
        self,
        state,
        *,
        allow_discards: bool,
        play_width: int | None = None,
        discard_width: int | None = None,
    ):
        root_beam = self.nodes_evaluated == 0
        actions = super()._candidate_actions(
            state,
            allow_discards=allow_discards,
            play_width=play_width,
            discard_width=discard_width,
        )
        if not root_beam:
            return actions

        blind = getattr(state, "blind", None)
        if getattr(blind, "type", None) == BlindType.BOSS:
            return actions

        for recommendation in self.consumable_timing_policy.blind_clear_recommendations(
            state
        ):
            # The Sun retains its separately validated multi-target escape path.
            # This integration covers the remaining deterministic B6/D5/D6 uses.
            if str(getattr(recommendation.consumable, "name", "")) == "The Sun":
                continue

            action = recommendation.to_action()
            if action is None:
                continue
            estimate = self._estimate_from_recommendation(state, action, recommendation)
            if estimate is None:
                continue

            self._integrated_consumable_estimates[id(action)] = estimate
            return [*actions, action]

        return actions

    def _estimate_action(self, state, action: BalatroAction, depth: int):
        if action.name != USE_CONSUMABLE:
            return super()._estimate_action(state, action, depth)

        estimate = self._integrated_consumable_estimates.get(id(action))
        if estimate is None:
            estimate = self._matching_integrated_estimate(state, action)
        if estimate is not None:
            self._consume_node()
            return estimate

        return super()._estimate_action(state, action, depth)

    def _matching_integrated_estimate(
        self,
        state,
        action: BalatroAction,
    ) -> _ActionEstimate | None:
        """Rebuild a cached estimate for confirmation/root-action evaluation."""
        for recommendation in self.consumable_timing_policy.blind_clear_recommendations(
            state
        ):
            if str(getattr(recommendation.consumable, "name", "")) == "The Sun":
                continue
            candidate = recommendation.to_action()
            if candidate is None:
                continue
            if candidate.target is not action.target:
                continue
            if self._selected_identity(candidate) != self._selected_identity(action):
                continue
            return self._estimate_from_recommendation(state, action, recommendation)
        return None

    @staticmethod
    def _selected_identity(action: BalatroAction) -> tuple[int, ...]:
        return tuple(sorted(id(card) for card in action.cards))

    @staticmethod
    def _estimate_from_recommendation(
        state,
        action: BalatroAction,
        recommendation,
    ) -> _ActionEstimate | None:
        after = recommendation.after_projection
        before = recommendation.before_projection
        if (
            before is None
            or after is None
            or not before.joker_projection_complete
            or not after.joker_projection_complete
            or before.clears_blind
            or not after.clears_blind
        ):
            return None

        return _ActionEstimate(
            action=action,
            value=LiveBlindPlanValue(
                clear_probability=1.0,
                expected_progress=1.0,
                expected_score=float(after.expected_projected_total),
                expected_hands_remaining=float(
                    max(0, int(getattr(state, "hands_remaining", 0)) - 1)
                ),
                expected_discards_remaining=float(
                    getattr(state, "discards_remaining", 0)
                ),
            ),
            exact=True,
        )
