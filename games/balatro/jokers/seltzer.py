from games.balatro.joker import Joker, JokerContext


class SeltzerJoker(Joker):

    def __init__(self):
        self.rounds_remaining = 10

    def apply(self, context: JokerContext) -> JokerContext:
        if self.rounds_remaining <= 0:
            return context

        context.data["retrigger_played_cards"] = (
            context.data.get("retrigger_played_cards", 0) + 1
        )

        if context.trigger == "ROUND_ENDED":
            self.rounds_remaining -= 1

        return context