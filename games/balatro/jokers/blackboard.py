from games.balatro.joker import Joker, JokerContext


class BlackboardJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.held_cards and all(
            card.suit in ("Spades", "Clubs")
            for card in context.held_cards
        ):
            context.score.x_mult *= 3

        return context