from games.balatro.joker import Joker, JokerContext


class LustyJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        context.score.mult += sum(
            card.suit == "Hearts"
            for card in scoring_cards
        ) * 3

        return context
