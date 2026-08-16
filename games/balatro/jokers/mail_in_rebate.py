from games.balatro.joker import Joker, JokerContext


class MailInRebateJoker(Joker):

    def __init__(self, rank: str):
        self.rank = str(rank)

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "DISCARD":
            return context

        discarded = sum(
            str(card.rank) == self.rank
            for card in context.cards
        )
        if discarded:
            context.state.money = (
                int(getattr(context.state, "money", 0) or 0)
                + discarded * 5
            )

        return context
