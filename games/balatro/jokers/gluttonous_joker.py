from games.balatro.joker import Joker, JokerContext


class GluttonousJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        mult = sum(
            card.suit == "Clubs"
            for card in scoring_cards
        ) * 3

        context.score.mult += mult

        return context
