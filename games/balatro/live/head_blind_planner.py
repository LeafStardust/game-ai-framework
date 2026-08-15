from __future__ import annotations

from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.scoring import BalatroScorer


class HeadScorer(BalatroScorer):
    """Balatro scorer with The Head's Hearts debuff applied.

    Debuffed cards still participate in poker-hand classification, but their card
    chips and card/held modifier effects are disabled by ``BalatroScorer``'s
    debuff hook. Suit matching intentionally uses the card model's normal rules:
    Wild cards match every suit while Stone cards match no suit.
    """

    DEBUFFED_SUIT = "Hearts"

    def is_card_debuffed(self, card) -> bool:
        if super().is_card_debuffed(card):
            return True
        matches_suit = getattr(card, "matches_suit", None)
        if callable(matches_suit):
            return bool(matches_suit(self.DEBUFFED_SUIT))
        return str(getattr(card, "suit", "")) == self.DEBUFFED_SUIT


class HeadHandDecisionEvaluator(LiveHandDecisionEvaluator):
    """Live hand evaluator whose visible score projection models The Head."""

    def __init__(self):
        super().__init__()
        self.scorer = HeadScorer()
        self.score_outcomes = VisibleCardScoreOutcomeModel(self.scorer)


class HeadBlindClearPlanner(LiveBlindClearPlanner):
    """Bounded public-state blind-clear planner for The Head."""

    BOSS_NAME = "The Head"

    def __init__(self, *, evaluator=None, **kwargs):
        super().__init__(
            evaluator=evaluator or HeadHandDecisionEvaluator(),
            **kwargs,
        )

    @classmethod
    def supports(cls, state) -> bool:
        return getattr(state, "boss_name", None) == cls.BOSS_NAME

    def _require_state(self, state) -> None:
        super()._require_state(state)
        boss_name = getattr(state, "boss_name", None)
        if boss_name != self.BOSS_NAME:
            raise ValueError(
                f"Head planner requires {self.BOSS_NAME}, observed {boss_name!r}"
            )
