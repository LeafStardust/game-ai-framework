from games.balatro.joker import Joker, JokerContext


class DaggerJoker(Joker):

    def __init__(self):
        self.mult = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "BLIND_SELECTED":
            jokers = getattr(context.state, "jokers", [])

            try:
                index = jokers.index(self)
            except ValueError:
                return context

            if index + 1 >= len(jokers):
                return context

            target = jokers[index + 1]
            # Eternal Jokers cannot be destroyed by Ceremonial Dagger. Balatro
            # therefore leaves both Jokers in place and grants no permanent Mult;
            # keep the modeled trigger consistent with the pre-blind order policy.
            if bool(getattr(target, "eternal", False)):
                return context

            sell_value = max(
                0,
                int(
                    getattr(
                        target,
                        "sell_value",
                        getattr(target, "sell_cost", 0),
                    )
                    or 0
                ),
            )
            self.mult += 2 * sell_value
            context.data["destroy_joker"] = target
            return context

        if context.score is not None:
            context.score.mult += self.mult

        return context
