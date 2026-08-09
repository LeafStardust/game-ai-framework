from games.balatro.joker import Joker, JokerContext


class RocketJoker(Joker):

    def __init__(self):
        self.money = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "ROUND_ENDED":
            self.money += 1

            if context.data.get("boss_blind"):
                self.money += 2

            context.data["money"] = (
                context.data.get("money", 0) + self.money
            )

        return context