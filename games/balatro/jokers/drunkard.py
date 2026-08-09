from games.balatro.joker import Joker, JokerContext


class DrunkardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["discards_per_round_modifier"] = (
            context.data.get(
                "discards_per_round_modifier",
                0
            ) + 1
        )

        return context