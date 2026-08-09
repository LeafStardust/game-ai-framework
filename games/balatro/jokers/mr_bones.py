from games.balatro.joker import Joker, JokerContext


class MrBonesJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "RUN_FAILED":
            return context

        if context.data.get("score", 0) >= context.data.get(
            "required_score",
            0
        ) * 0.25:
            context.data["prevented_loss"] = True

        return context