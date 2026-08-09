from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class FortuneTellerJoker(Joker):

    def __init__(self):
        self.mult = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if (
            context.event is not None
            and context.event.type == BalatroEventType.TAROT_USED
        ):
            self.mult += 1
            return context

        if context.score is not None:
            context.score.mult += self.mult

        return context