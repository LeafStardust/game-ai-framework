from framework.core.action import Action
from framework.core.state import GameState

from games.balatro.blinds.base import BlindModifier


class DisableFirstCardModifier(BlindModifier):

    def apply(
        self,
        state: GameState,
        action: Action
    ) -> bool:

        if hasattr(action, "cards") and action.cards:

            action.cards = action.cards[1:]

        return True