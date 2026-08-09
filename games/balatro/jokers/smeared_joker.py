from games.balatro.joker import Joker, JokerContext


class SmearedJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["smeared_suits"] = {
            "Hearts": "Red",
            "Diamonds": "Red",
            "Clubs": "Black",
            "Spades": "Black",
        }

        return context