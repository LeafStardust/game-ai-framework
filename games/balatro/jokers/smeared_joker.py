from games.balatro.joker import Joker, JokerContext


class SmearedJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger not in {"", "HAND_RULES"}:
            return context
        context.data["smeared_suits"] = {
            "Hearts": "Red",
            "Diamonds": "Red",
            "Clubs": "Black",
            "Spades": "Black",
        }
        return context
