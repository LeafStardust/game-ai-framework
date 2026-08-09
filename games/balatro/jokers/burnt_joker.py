from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class BurntJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.event is None:
            return context

        if context.event.type != BalatroEventType.CARDS_DISCARDED:
            return context

        cards = context.event.cards or []

        if len(cards) == 1:
            context.data["level_up_hand"] = context.data.get(
                "discarded_hand"
            )

        return context