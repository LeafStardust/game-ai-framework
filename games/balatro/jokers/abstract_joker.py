from games.balatro.joker import Joker, JokerContext


class AbstractJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        joker_count = len(
            getattr(context.state, "jokers", [])
        )

        context.score.mult += joker_count * 3

        return context