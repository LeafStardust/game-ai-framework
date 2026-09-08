from games.balatro.joker import Joker, JokerContext


class BlueJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        context.score.chips += len(getattr(context.state, "deck", []) or []) * 2

        return context
