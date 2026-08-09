from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class HologramJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:

        if (
            context.event is not None
            and context.event.type == BalatroEventType.CARDS_ADDED
        ):
            self.x_mult += 0.25 * len(
                context.event.cards or []
            )

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context