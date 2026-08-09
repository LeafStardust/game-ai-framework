from games.balatro.joker import Joker, JokerContext


class SwashbucklerJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        jokers = getattr(
            context.state,
            "jokers",
            []
        )

        context.score.mult += sum(
            getattr(joker, "sell_value", 0)
            for joker in jokers
            if joker is not self
        )

        return context