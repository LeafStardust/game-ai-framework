from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class GreenJoker(Joker):

    def __init__(self):
        self.mult = 0

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.event is None:
            return context

        if context.event.type == BalatroEventType.HAND_SCORED:
            self.mult += 1

            if context.score is not None:
                context.score.mult += self.mult

        elif context.event.type == BalatroEventType.CARDS_DISCARDED:
            self.mult = max(
                0,
                self.mult - 1
            )

        return context