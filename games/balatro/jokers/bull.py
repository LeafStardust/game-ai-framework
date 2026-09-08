from games.balatro.joker import Joker, JokerContext


class BullJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        money = max(0, int(getattr(context.state, "money", 0) or 0))
        context.score.chips += money * 2

        return context
