import random

from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class ToDoListJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        target = context.data.get("to_do_list_hand")

        if target is None:
            target = random.choice(list(PokerHand))
            context.data["to_do_list_hand"] = target

        if (
            context.trigger == "HAND_SCORED"
            and context.poker_hand == target
        ):
            context.data.setdefault(
                "money",
                0
            )
            context.data["money"] += 4
            context.data["to_do_list_hand"] = random.choice(
                list(PokerHand)
            )

        return context