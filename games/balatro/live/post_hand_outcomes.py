from __future__ import annotations

from copy import deepcopy
from math import comb

from games.balatro.hand_rules import card_is_face, hand_rules_for_state
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.live.score_outcomes import (
    ScoreOutcome,
    ScoreOutcomeDistribution,
    ScoreProjectionTransition,
    VisibleCardScoreOutcomeModel,
    _ProjectedStochasticScorer,
)
from games.balatro.scoring import BalatroScorer


class _LiveOnScoredScorer(BalatroScorer):
    ON_SCORED_JOKER_CLASS_NAMES = (
        BalatroScorer.ON_SCORED_JOKER_CLASS_NAMES
        | frozenset({"BusinessCardJoker"})
    )


class _LiveProjectedStochasticScorer(_ProjectedStochasticScorer):
    ON_SCORED_JOKER_CLASS_NAMES = (
        _ProjectedStochasticScorer.ON_SCORED_JOKER_CLASS_NAMES
        | frozenset({"BusinessCardJoker"})
    )


class _LiveOutcomeJokerProjector(LiveJokerScoreProjector):
    SUPPORTED_CLASS_NAMES = (
        LiveJokerScoreProjector.SUPPORTED_CLASS_NAMES
        | frozenset({"BusinessCardJoker"})
    )


class LiveVisibleCardScoreOutcomeModel(VisibleCardScoreOutcomeModel):
    """Extend visible score outcomes with exact live state RNG branches."""

    SPACE_JOKER_PROBABILITY = 0.25
    BUSINESS_CARD_PROBABILITY = 0.5
    BUSINESS_CARD_REWARD = 2

    def __init__(
        self,
        scorer: BalatroScorer | None = None,
        joker_projector: LiveJokerScoreProjector | None = None,
    ):
        if joker_projector is not None:
            super().__init__(scorer=scorer, joker_projector=joker_projector)
            return

        live_scorer = (
            scorer
            if isinstance(scorer, _LiveOnScoredScorer)
            else _LiveOnScoredScorer()
        )
        super().__init__(
            scorer=live_scorer,
            joker_projector=_LiveOutcomeJokerProjector(live_scorer),
        )

    def project_transition(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ) -> ScoreProjectionTransition:
        transition = self._project_scoring_transition(
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

    def _project_scoring_transition(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool,
    ) -> ScoreProjectionTransition:
        business_cards = len(self._jokers_named(state, "BusinessCardJoker"))
        if business_cards <= 0:
            return super().project_transition(
                hand,
                state,
                cards,
                include_card_chips=include_card_chips,
            )

        probe = self.joker_projector.score(
            hand,
            state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )
        projected_state = probe.state_after_scoring
        rules = hand_rules_for_state(projected_state)
        triggers = self._business_card_scoring_triggers(
            hand,
            probe.cards_after_copy,
            projected_state,
            rules=rules,
            extra_retriggers=probe.played_card_retriggers,
        )
        if triggers <= 0:
            return super().project_transition(
                hand,
                state,
                cards,
                include_card_chips=include_card_chips,
            )

        outcomes = []
        inner_random_sources: tuple[str, ...] = ()
        for successes, probability in self._business_card_branches(
            triggers,
            projected_state,
        ):
            branch_state = state.copy()
            branch_state.money = (
                int(getattr(branch_state, "money", 0) or 0)
                + self.BUSINESS_CARD_REWARD * successes
            )
            branch_transition = super().project_transition(
                hand,
                branch_state,
                cards,
                include_card_chips=include_card_chips,
            )
            inner_random_sources = branch_transition.distribution.random_sources
            for outcome in branch_transition.distribution.outcomes:
                outcomes.append(
                    ScoreOutcome(
                        score=outcome.score,
                        probability=outcome.probability * probability,
                        state_after_scoring=outcome.state_after_scoring,
                    )
                )

        distribution = ScoreOutcomeDistribution(
            outcomes=tuple(outcomes),
            random_sources=(
                *inner_random_sources,
                f"Business Card x{triggers}",
            ),
        )
        return ScoreProjectionTransition(
            distribution=distribution,
            state_after_scoring=projected_state,
            unsupported_jokers=probe.unsupported_jokers,
        )

    def _business_card_scoring_triggers(
        self,
        hand,
        cards,
        state,
        *,
        rules: dict | None = None,
        extra_retriggers: int = 0,
    ) -> int:
        copies = len(self._jokers_named(state, "BusinessCardJoker"))
        if copies <= 0:
            return 0

        face_triggers = 0
        for card in self.scorer.scoring_cards(hand, cards, rules=rules):
            if self.scorer.is_card_debuffed(card):
                continue
            if not card_is_face(card, rules):
                continue
            face_triggers += self.scorer._played_card_trigger_count(
                card,
                extra_retriggers,
            )
        return copies * face_triggers

    def _business_card_branches(
        self,
        triggers: int,
        state,
    ) -> tuple[tuple[int, float], ...]:
        probability = self._listed_probability(
            self.BUSINESS_CARD_PROBABILITY,
            state,
        )
        branches = []
        for successes in range(triggers + 1):
            branch_probability = (
                comb(triggers, successes)
                * (probability ** successes)
                * ((1.0 - probability) ** (triggers - successes))
            )
            if branch_probability > 0.0:
                branches.append((successes, branch_probability))
        return tuple(branches)

    def _project_stochastic_branch(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool,
        lucky_branch,
        bloodstone_branch,
    ):
        branch_state = self._lucky_branch_input_state(state, lucky_branch)
        branch_scorer = _LiveProjectedStochasticScorer(
            lucky_mult_results=lucky_branch.mult_results,
            bloodstone_results=bloodstone_branch.results,
        )
        branch_projector = _LiveOutcomeJokerProjector(branch_scorer)
        return branch_projector.score(
            hand,
            branch_state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
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
