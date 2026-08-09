from games.balatro.joker import Joker, JokerContext


class BootstrapsJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        money = getattr(context.state, "money", 0)
        increments = money // 5

        context.score.chips += increments
        context.score.mult += increments * 2

        return context