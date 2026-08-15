from games.balatro.joker import Joker, JokerContext


class ScaryFaceJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        faces = sum(
            card.rank in {"J", "Q", "K"}
            for card in scoring_cards
        )

        context.score.chips += faces * 30

        return context
