from games.balatro.joker import Joker, JokerContext


class OnyxAgateJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:

        if context.score is None:
            return context

        clubs = sum(
            card.suit == "Clubs"
            for card in context.cards
        )

        context.score.mult += clubs * 7

        return context