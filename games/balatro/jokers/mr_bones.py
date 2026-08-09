from games.balatro.joker import Joker, JokerContext


class MrBonesJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "RUN_FAILED":
            return context

        score = context.data.get("score", 0)
        required_score = context.data.get("required_score", 0)

        if score >= required_score * 0.25:
            context.data["prevented_loss"] = True

        return context