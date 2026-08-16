from __future__ import annotations

from copy import deepcopy

from games.balatro.live.final_joker_outcomes import (
    LiveFinalJokerScoreOutcomeModel,
    LiveFinalJokerScoreProjector,
    _FinalLiveScorer,
    _FinalProjectedStochasticScorer,
)
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.score_outcomes import (
    ScoreOutcome,
    ScoreOutcomeDistribution,
    ScoreProjectionTransition,
)


class _DebuffedJokerProxy:
    """Metadata-only Joker placeholder for Crimson Heart-disabled Jokers."""

    def __init__(self, joker):
        self._original = joker
        self.debuffed = True
        for field in (
            "live_id",
            "area_index",
            "center",
            "label",
            "rarity",
            "cost",
            "sell_cost",
        ):
            if hasattr(joker, field):
                setattr(self, field, getattr(joker, field))
        # A debuffed Joker's Edition is disabled with its own ability. Rarity is
        # intentionally preserved because Baseball Card still reacts to a debuffed
        # Uncommon Joker in vanilla Balatro.
        self.edition = None

    def apply(self, context):
        return context


class CrimsonHeartJokerScoreProjector(LiveFinalJokerScoreProjector):
    @classmethod
    def supports_in_state(cls, joker, state) -> bool:
        if isinstance(joker, _DebuffedJokerProxy):
            return True
        return super().supports_in_state(joker, state)


class CrimsonHeartScoreOutcomeModel(LiveFinalJokerScoreOutcomeModel):
    """Exact current-hand + next-Joker Crimson Heart projection.

    The current disabled Joker is authoritative live state. After each hand,
    Balatro clears all Joker debuffs and chooses uniformly from Jokers that were
    not disabled on the previous hand (unless only one Joker exists). This model
    branches that small public set exactly without sampling hidden RNG.
    """

    RANDOM_SOURCE = "Crimson Heart next disabled Joker"

    def __init__(self) -> None:
        scorer = _FinalLiveScorer()
        super().__init__(
            scorer=scorer,
            joker_projector=CrimsonHeartJokerScoreProjector(scorer),
        )

    def project_transition(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ) -> ScoreProjectionTransition:
        wrapped_state = self._wrap_current_debuffs(state)
        transition = super().project_transition(
            hand,
            wrapped_state,
            cards,
            include_card_chips=include_card_chips,
        )
        self._unwrap_transition_states(transition)
        return self._branch_next_disabled_joker(transition)

    def _project_stochastic_branch(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool,
        lucky_branch,
        bloodstone_branch,
        misprint_results: tuple[int, ...] = (),
    ):
        branch_state = self._lucky_branch_input_state(state, lucky_branch)
        branch_scorer = _FinalProjectedStochasticScorer(
            lucky_mult_results=lucky_branch.mult_results,
            bloodstone_results=bloodstone_branch.results,
            misprint_results=misprint_results,
        )
        branch_projector = CrimsonHeartJokerScoreProjector(branch_scorer)
        return branch_projector.score(
            hand,
            branch_state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )

    @staticmethod
    def _wrap_current_debuffs(state):
        if state is None:
            return None
        wrapped = state.copy()
        wrapped.jokers = [
            _DebuffedJokerProxy(deepcopy(joker))
            if bool(getattr(joker, "debuffed", False))
            else deepcopy(joker)
            for joker in getattr(state, "jokers", [])
        ]
        return wrapped

    @classmethod
    def _unwrap_state(cls, state) -> None:
        if state is None:
            return
        state.jokers = [
            joker._original
            if isinstance(joker, _DebuffedJokerProxy)
            else joker
            for joker in getattr(state, "jokers", [])
        ]

    @classmethod
    def _unwrap_transition_states(cls, transition) -> None:
        seen = set()
        states = [transition.state_after_scoring]
        states.extend(
            outcome.state_after_scoring
            for outcome in transition.distribution.outcomes
        )
        for state in states:
            if state is None or id(state) in seen:
                continue
            seen.add(id(state))
            cls._unwrap_state(state)

    def _branch_next_disabled_joker(
        self,
        transition: ScoreProjectionTransition,
    ) -> ScoreProjectionTransition:
        outcomes: list[ScoreOutcome] = []
        random_sources = transition.distribution.random_sources
        branched = False

        for outcome in transition.distribution.outcomes:
            source = (
                outcome.state_after_scoring
                if outcome.state_after_scoring is not None
                else transition.state_after_scoring
            )
            if source is None:
                outcomes.append(outcome)
                continue

            jokers = list(getattr(source, "jokers", []))
            if not jokers:
                outcomes.append(outcome)
                continue

            # Chicot disables the boss before Crimson Heart can choose a Joker.
            if any(type(joker).__name__ == "ChicotJoker" for joker in jokers):
                outcomes.append(outcome)
                continue

            if len(jokers) < 2:
                candidates = [0]
            else:
                candidates = [
                    index
                    for index, joker in enumerate(jokers)
                    if not bool(getattr(joker, "debuffed", False))
                ]
            if not candidates:
                outcomes.append(outcome)
                continue

            branched = branched or len(candidates) > 1
            probability = outcome.probability / len(candidates)
            for selected_index in candidates:
                branch = deepcopy(source)
                for index, joker in enumerate(branch.jokers):
                    joker.debuffed = index == selected_index
                outcomes.append(
                    ScoreOutcome(
                        score=outcome.score,
                        probability=probability,
                        state_after_scoring=branch,
                    )
                )

        if not outcomes:
            return transition
        if branched and self.RANDOM_SOURCE not in random_sources:
            random_sources = (*random_sources, self.RANDOM_SOURCE)

        common_state = (
            outcomes[0].state_after_scoring
            if len(outcomes) == 1
            else None
        )
        return ScoreProjectionTransition(
            distribution=ScoreOutcomeDistribution(
                outcomes=tuple(outcomes),
                random_sources=tuple(random_sources),
            ),
            state_after_scoring=common_state,
            unsupported_jokers=transition.unsupported_jokers,
        )


class CrimsonHeartHandDecisionEvaluator(LiveHandDecisionEvaluator):
    def __init__(self):
        super().__init__()
        self.score_outcomes = CrimsonHeartScoreOutcomeModel()
