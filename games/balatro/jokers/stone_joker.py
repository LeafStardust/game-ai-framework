from games.balatro.joker import Joker, JokerContext


class StoneJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        stone_cards = sum(
            card.enhancement == "Stone"
            for card in context.cards
        )

        context.score.chips += stone_cards * 25

        return context