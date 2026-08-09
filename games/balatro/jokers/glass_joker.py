from games.balatro.joker import Joker, JokerContext


class GlassJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        destroyed = getattr(
            context.state,
            "glass_cards_destroyed",
            0
        )

        context.score.x_mult *= 1 + (0.75 * destroyed)

        return context