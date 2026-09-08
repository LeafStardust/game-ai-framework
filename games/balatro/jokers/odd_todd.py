from games.balatro.joker import Joker, JokerContext


class OddToddJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        odd_ranks = {
            "A",
            "3",
            "5",
            "7",
            "9"
        }
        scoring_cards = context.data.get("scoring_cards", context.cards)

        context.score.chips += sum(
            card.rank in odd_ranks
            for card in scoring_cards
        ) * 31

        return context
