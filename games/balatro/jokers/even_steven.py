from games.balatro.joker import Joker, JokerContext


class EvenStevenJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        even_ranks = {
            "2",
            "4",
            "6",
            "8",
            "10"
        }
        scoring_cards = context.data.get("scoring_cards", context.cards)

        context.score.mult += sum(
            card.rank in even_ranks
            for card in scoring_cards
        ) * 4

        return context
