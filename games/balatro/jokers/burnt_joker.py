from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext
from games.balatro.mechanics import DISCARD_HAND_LEVELING


class BurntJoker(Joker):
    mechanics = frozenset({DISCARD_HAND_LEVELING})

    def apply(self, context: JokerContext) -> JokerContext:
        if context.event is None:
            return context

        if context.event.type != BalatroEventType.CARDS_DISCARDED:
            return context

        # Generic semantic probes historically omitted round-history context, so
        # absence keeps the standalone Joker behavior as a first-discard probe.
        # Live projection always supplies this flag explicitly.
        if not bool(context.data.get("first_discard", True)):
            return context

        discarded_hand = context.data.get("discarded_hand")
        if discarded_hand is None:
            return context

        context.data["level_up_hand"] = discarded_hand
        context.data.setdefault("level_up_hands", []).append(discarded_hand)
        return context
