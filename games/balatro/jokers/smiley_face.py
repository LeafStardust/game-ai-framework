from games.balatro.joker import Joker, JokerContext


class SmileyFaceJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        faces = sum(
            card.rank in {"J", "Q", "K"}
            for card in scoring_cards
        )

        context.score.mult += faces * 5

        return context
