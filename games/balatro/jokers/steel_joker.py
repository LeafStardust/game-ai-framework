from games.balatro.joker import Joker, JokerContext


class SteelJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        steel_cards = sum(
            card.enhancement == "Steel"
            for card in context.state.deck
        )

        context.score.x_mult *= 1 + (0.2 * steel_cards)

        return context