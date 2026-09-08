from games.balatro.joker import Joker, JokerContext


class BootstrapsJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        money = int(getattr(context.state, "money", 0) or 0)
        increments = max(0, money // 5)

        context.score.mult += increments * 2

        return context
