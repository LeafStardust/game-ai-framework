from games.balatro.joker import Joker, JokerContext


class SmileyFaceJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        faces = sum(
            card.rank in {"J", "Q", "K"}
            for card in context.cards
        )

        context.score.mult += faces * 5

        return context