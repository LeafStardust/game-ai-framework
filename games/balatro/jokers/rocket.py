from games.balatro.joker import Joker, JokerContext


class RocketJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        money = 3 if context.data.get("boss_blind") else 1

        context.data["money"] = (
            context.data.get("money", 0) + money
        )

        return context