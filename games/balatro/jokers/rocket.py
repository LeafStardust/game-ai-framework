from games.balatro.joker import Joker, JokerContext


class RocketJoker(Joker):

    def __init__(self):
        self.dollars = 1
        self.increase = 2

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        if context.data.get("boss_blind") is True:
            self.dollars += self.increase
        context.data["money"] = context.data.get("money", 0) + self.dollars

        return context
