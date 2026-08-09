from games.balatro.joker import Joker, JokerContext


class BlueJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        deck_size = len(
            context.data.get("deck", [])
        )

        context.score.chips += deck_size * 2

        return context