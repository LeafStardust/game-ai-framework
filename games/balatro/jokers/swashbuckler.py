from games.balatro.joker import Joker, JokerContext


class SwashbucklerJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        context.score.mult += sum(
            self._sell_value(joker)
            for joker in getattr(context.state, "jokers", [])
            if joker is not self
        )
        return context

    @staticmethod
    def _sell_value(joker) -> int:
        value = getattr(joker, "sell_cost", None)
        if value is None:
            value = getattr(joker, "sell_value", 0)
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0
