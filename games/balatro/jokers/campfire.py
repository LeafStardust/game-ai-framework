from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class CampfireJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.event is not None:
            if context.event.type == BalatroEventType.CARD_SOLD:
                self.x_mult += 0.25

            elif context.event.type == BalatroEventType.BOSS_BLIND_DEFEATED:
                self.x_mult = 1.0

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context