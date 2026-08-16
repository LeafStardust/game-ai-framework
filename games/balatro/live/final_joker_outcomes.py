from __future__ import annotations

from games.balatro.live.generated_consumable_outcomes import (
    LiveGeneratedConsumableScoreOutcomeModel,
    _GeneratedConsumableOutcomeJokerProjector,
)
from games.balatro.live.post_hand_outcomes import (
    _LiveOnScoredScorer,
    _LiveProjectedStochasticScorer,
)
from games.balatro.scoring import BalatroScorer


class _FinalOutcomeJokerProjector(_GeneratedConsumableOutcomeJokerProjector):
    """Final live scorer admission layer for ordered deterministic effects."""

    SUPPORTED_CLASS_NAMES = (
        _GeneratedConsumableOutcomeJokerProjector.SUPPORTED_CLASS_NAMES
        | frozenset({"ToDoListJoker"})
    )

    @classmethod
    def supports_in_state(cls, joker, state) -> bool:
        if type(joker).__name__ == "ToDoListJoker":
            # The target is a public per-card ability field. If it was not observed,
            # or is a secret hand the current PokerHand model cannot represent yet,
            # fail closed rather than inventing a target or reward.
            if getattr(joker, "target_hand", None) is None:
                return False
        return super().supports_in_state(joker, state)


class LiveFinalJokerScoreOutcomeModel(LiveGeneratedConsumableScoreOutcomeModel):
    """Current complete D1 outcome stack, including ordered To Do List economy."""

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
            if isinstance(scorer, _LiveOnScoredScorer)
            else _LiveOnScoredScorer()
        )
        super().__init__(
            scorer=live_scorer,
            joker_projector=_FinalOutcomeJokerProjector(live_scorer),
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
        """Preserve To Do List admission inside nested visible-RNG branches."""
        branch_state = self._lucky_branch_input_state(state, lucky_branch)
        branch_scorer = _LiveProjectedStochasticScorer(
            lucky_mult_results=lucky_branch.mult_results,
            bloodstone_results=bloodstone_branch.results,
            misprint_results=misprint_results,
        )
        branch_projector = _FinalOutcomeJokerProjector(branch_scorer)
        return branch_projector.score(
            hand,
            branch_state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )
