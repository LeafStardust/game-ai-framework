from games.balatro.joker import Joker, JokerContext


class JugglerJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["hand_size_modifier"] = (
            context.data.get("hand_size_modifier", 0) + 1
        )

        return context