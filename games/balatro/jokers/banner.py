from games.balatro.joker import Joker, JokerContext


class BannerJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        chips = context.state.discards_remaining * 30
        context.score.chips += chips

        return context