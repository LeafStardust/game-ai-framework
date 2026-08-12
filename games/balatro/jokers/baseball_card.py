from games.balatro.joker import Joker, JokerContext


class BaseballCardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        uncommon_jokers = sum(
            str(getattr(joker, "rarity", "")).upper() == "UNCOMMON"
            for joker in getattr(context.state, "jokers", [])
            if joker is not self
        )

        context.score.x_mult *= 1.5 ** uncommon_jokers

        return context
