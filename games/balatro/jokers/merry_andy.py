from games.balatro.joker import Joker, JokerContext


class MerryAndyJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "JOKER_ACQUIRED":
            return context

        context.data["hand_size_modifier"] = (
            context.data.get("hand_size_modifier", 0) + 3
        )
        context.data["discards_per_round_modifier"] = (
            context.data.get("discards_per_round_modifier", 0) + 1
        )

        return context