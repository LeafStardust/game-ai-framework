from games.balatro.joker import Joker, JokerContext


class GlassJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        context.score.x_mult *= (
            1 + (0.75 * context.state.glass_cards_destroyed)
        )

        return context