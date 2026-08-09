from games.balatro.joker import Joker, JokerContext


class MatadorJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "BOSS_BLIND_DEFEATED":
            return context

        context.data["money"] = (
            context.data.get("money", 0) + 8
        )

        return context