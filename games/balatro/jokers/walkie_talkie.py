from games.balatro.joker import Joker, JokerContext


class WalkieTalkieJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        ranks = {"10", "4"}

        count = sum(
            card.rank in ranks
            for card in context.cards
        )

        if context.score is not None:
            context.score.chips += count * 10
            context.score.mult += count * 4

        return context