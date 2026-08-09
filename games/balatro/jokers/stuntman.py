from games.balatro.joker import Joker, JokerContext


class StuntmanJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.chips += 300

        context.data["hand_size_modifier"] = (
            context.data.get("hand_size_modifier", 0) - 2
        )

        return context