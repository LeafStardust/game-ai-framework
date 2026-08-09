from games.balatro.joker import Joker, JokerContext


class DaggerJoker(Joker):

    def __init__(self):
        self.mult = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "BLIND_SELECTED":
            return context

        jokers = getattr(context.state, "jokers", [])

        try:
            index = jokers.index(self)
        except ValueError:
            return context

        if index + 1 >= len(jokers):
            return context

        target = jokers[index + 1]

        self.mult += 2 * getattr(target, "sell_value", 0)
        context.data["destroy_joker"] = target

        return context