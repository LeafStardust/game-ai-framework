from __future__ import annotations

from copy import deepcopy
from math import comb

from games.balatro.live.score_outcomes import (
    ScoreOutcome,
    ScoreOutcomeDistribution,
    ScoreProjectionTransition,
    VisibleCardScoreOutcomeModel,
)


class LiveVisibleCardScoreOutcomeModel(VisibleCardScoreOutcomeModel):
    """Extend visible score outcomes with exact post-hand live state RNG."""

    SPACE_JOKER_PROBABILITY = 0.25

    def project_transition(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ) -> ScoreProjectionTransition:
        transition = super().project_transition(
            hand,
            state,
            cards,
            include_card_chips=include_card_chips,
        )
        projected_state = transition.state_after_scoring
        space_jokers = len(self._jokers_named(projected_state, "SpaceJoker"))
        if space_jokers <= 0:
            return transition

        branches = self._space_joker_branches(space_jokers, projected_state)
        outcomes = []
        for score_outcome in transition.distribution.outcomes:
            source_state = (
                score_outcome.state_after_scoring
                if score_outcome.state_after_scoring is not None
                else projected_state
            )
            for level_ups, probability in branches:
                branch_state = deepcopy(source_state)
                self._apply_space_joker_level_ups(branch_state, hand, level_ups)
                outcomes.append(
                    ScoreOutcome(
                        score=score_outcome.score,
                        probability=score_outcome.probability * probability,
                        state_after_scoring=branch_state,
                    )
                )

        distribution = ScoreOutcomeDistribution(
            outcomes=tuple(outcomes),
            random_sources=(
                *transition.distribution.random_sources,
                f"Space Joker x{space_jokers}",
            ),
        )
        return ScoreProjectionTransition(
            distribution=distribution,
            state_after_scoring=projected_state,
            unsupported_jokers=transition.unsupported_jokers,
        )

    def _space_joker_branches(self, copies: int, state) -> tuple[tuple[int, float], ...]:
        probability = self._listed_probability(
            self.SPACE_JOKER_PROBABILITY,
            state,
        )
        branches = []
        for successes in range(copies + 1):
            branch_probability = (
                comb(copies, successes)
                * (probability ** successes)
                * ((1.0 - probability) ** (copies - successes))
            )
            if branch_probability > 0.0:
                branches.append((successes, branch_probability))
        return tuple(branches)

    @staticmethod
    def _apply_space_joker_level_ups(state, hand, level_ups: int) -> None:
        if state is None or level_ups <= 0:
            return
        levels = getattr(state, "hand_levels", None)
        if not isinstance(levels, dict):
            return

        key = hand.value
        current = int(levels.get(key, levels.get(hand, 1)) or 1)
        updated = current + int(level_ups)
        levels[key] = updated
        if hand in levels:
            levels[hand] = updated
