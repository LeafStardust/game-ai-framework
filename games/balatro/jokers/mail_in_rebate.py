from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.joker import Joker, JokerContext


MAIL_REBATE_RANKS = frozenset(HandEvaluator.RANK_ORDER)


class MailInRebateJoker(Joker):

    def __init__(self, rank: str):
        self.rank = str(rank)

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "DISCARD":
            return context

        discarded = sum(
            card.rank == self.rank and not card.debuffed and not card.is_stone
            for card in context.cards
        )
        if discarded:
            context.state.money = (
                int(getattr(context.state, "money", 0) or 0)
                + discarded * 5
            )

        return context
