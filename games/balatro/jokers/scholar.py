from games.balatro.joker import Joker, JokerContext


class ScholarJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        aces = sum(
            card.rank == "A"
            for card in scoring_cards
        )

        context.score.chips += aces * 20
        context.score.mult += aces * 4

        return context
