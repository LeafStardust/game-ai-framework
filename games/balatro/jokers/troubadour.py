from games.balatro.joker import Joker, JokerContext


class TroubadourJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["hand_size_modifier"] = (
            context.data.get("hand_size_modifier", 0) + 2
        )

        context.data["hands_per_round_modifier"] = (
            context.data.get("hands_per_round_modifier", 0) - 1
        )

        return context