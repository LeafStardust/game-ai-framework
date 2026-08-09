from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class PerkeoJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.event is None:
            return context

        if context.event.type != BalatroEventType.ROUND_ENDED:
            return context

        consumables = context.data.get("consumables", [])

        if not consumables:
            return context

        context.data["create_negative_copy"] = consumables[0]

        return context