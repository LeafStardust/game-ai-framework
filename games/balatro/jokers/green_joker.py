from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class GreenJoker(Joker):

    def __init__(self):
        self.mult = 0

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.trigger == "HAND_PLAYED":
            self.mult += 1
            return context
        if context.trigger == "DISCARD":
            self.mult = max(0, self.mult - 1)
            return context

        # Event-only lifecycle probes do not construct a phased scoring call.
        if context.trigger == "" and context.event is not None:
            if context.event.type == BalatroEventType.HAND_SCORED:
                self.mult += 1
            elif context.event.type == BalatroEventType.CARDS_DISCARDED:
                self.mult = max(0, self.mult - 1)

        if context.score is not None:
            context.score.mult += self.mult

        return context