from games.balatro.joker import Joker, JokerContext


class ScaryFaceJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        faces = sum(
            card.rank in {"J", "Q", "K"}
            for card in context.cards
        )

        context.score.chips += faces * 30

        return context