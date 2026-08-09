from games.balatro.joker import Joker, JokerContext


class SockAndBuskinJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        face_cards = [
            card
            for card in context.cards
            if card.rank in {"J", "Q", "K"}
        ]

        if face_cards:
            context.data["retrigger_cards"] = context.data.get(
                "retrigger_cards",
                0
            ) + len(face_cards)

        return context