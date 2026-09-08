from games.balatro.joker import Joker, JokerContext


class BannerJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        context.score.chips += (
            context.state.discards_remaining * 30
        )

        return context