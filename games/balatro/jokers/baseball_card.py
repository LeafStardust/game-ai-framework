from games.balatro.joker import Joker, JokerContext


class BaseballCardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        rare_jokers = sum(
            getattr(joker, "rarity", None) == "Rare"
            for joker in getattr(context.state, "jokers", [])
            if joker is not self
        )

        context.score.x_mult *= 1.5 ** rare_jokers

        return context