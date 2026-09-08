from games.balatro.joker import Joker, JokerContext


class StoneJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        owned_deck = getattr(context.state, "owned_deck", None)
        if owned_deck is None:
            return context

        stone_cards = sum(
            getattr(card, "enhancement", None) == "Stone"
            for card in owned_deck
        )
        context.score.chips += stone_cards * 25

        return context
