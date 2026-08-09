from games.balatro.joker import Joker, JokerContext


class CastleJoker(Joker):

    def __init__(self, suit: str):
        self.suit = suit
        self.chips = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.event is not None:
            cards = context.event.cards or []

            if context.event.type.value == "CARDS_DISCARDED":
                matching_cards = sum(
                    card.suit == self.suit
                    for card in cards
                )

                self.chips += matching_cards * 3
                return context

        if context.score is not None:
            context.score.chips += self.chips

        return context