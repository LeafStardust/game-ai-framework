from __future__ import annotations

from games.balatro.hand import PokerHand
from games.balatro.live.generated_consumable_outcomes import (
    LiveGeneratedConsumableScoreOutcomeModel,
    _GeneratedConsumableOutcomeJokerProjector,
)
from games.balatro.live.post_hand_outcomes import (
    _LiveOnScoredScorer,
    _LiveProjectedStochasticScorer,
)
from games.balatro.scoring import BalatroScorer, HandScore


_SECRET_HAND_SCORES = {
    PokerHand.FIVE_OF_A_KIND: HandScore(120, 12),
    PokerHand.FLUSH_HOUSE: HandScore(140, 14),
    PokerHand.FLUSH_FIVE: HandScore(160, 16),
}


class _FinalLiveScorer(_LiveOnScoredScorer):
    SCORES = {**BalatroScorer.SCORES, **_SECRET_HAND_SCORES}


class _FinalProjectedStochasticScorer(_LiveProjectedStochasticScorer):
    SCORES = {**BalatroScorer.SCORES, **_SECRET_HAND_SCORES}


class LiveFinalJokerScoreProjector(_GeneratedConsumableOutcomeJokerProjector):
    """Final D1 support contract for every admitted live Joker."""

    SUPPORTED_CLASS_NAMES = (
        _GeneratedConsumableOutcomeJokerProjector.SUPPORTED_CLASS_NAMES
        | frozenset({"ToDoListJoker"})
    )

    @classmethod
    def supports_in_state(cls, joker, state) -> bool:
        if type(joker).__name__ == "ToDoListJoker":
            # The target is a public per-card ability field. Absence means live
            # observation could not reconstruct the current request, so fail closed.
            if getattr(joker, "target_hand", None) is None:
                return False
        return super().supports_in_state(joker, state)


class LiveFinalJokerScoreOutcomeModel(LiveGeneratedConsumableScoreOutcomeModel):
    """Complete D1 outcome stack, including secret hands and To Do List economy."""

    def __init__(
        self,
        scorer: BalatroScorer | None = None,
        joker_projector=None,
    ) -> None:
        if joker_projector is not None:
            super().__init__(scorer=scorer, joker_projector=joker_projector)
            return

        live_scorer = (
            scorer
            if isinstance(scorer, _FinalLiveScorer)
            else _FinalLiveScorer()
        )
        super().__init__(
            scorer=live_scorer,
            joker_projector=LiveFinalJokerScoreProjector(live_scorer),
        )

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
        """Preserve final Joker support inside nested visible-RNG branches."""
        branch_state = self._lucky_branch_input_state(state, lucky_branch)
        branch_scorer = _FinalProjectedStochasticScorer(
            lucky_mult_results=lucky_branch.mult_results,
            bloodstone_results=bloodstone_branch.results,
            misprint_results=misprint_results,
        )
        branch_projector = LiveFinalJokerScoreProjector(branch_scorer)
        return branch_projector.score(
            hand,
            branch_state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )
