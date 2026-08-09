from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class RamenJoker(Joker):

    def __init__(self):
        self.x_mult = 2.0

    def apply(self, context: JokerContext) -> JokerContext:

        if context.event is not None:
            if context.event.type == BalatroEventType.CARDS_DISCARDED:
                self.x_mult = max(
                    1.0,
                    self.x_mult - 0.01 * len(context.event.cards or [])
                )

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context