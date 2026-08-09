from framework.core.environment import GameEnvironment
from framework.core.state import GameState
from framework.core.action import Action

from games.adapter import GameAdapter
from games.balatro.decks import BASE_DECK, BalatroDeck
from games.balatro.environment import BalatroEnvironment


class BalatroAdapter(GameAdapter):

    def __init__(
        self,
        deck: BalatroDeck = BASE_DECK
    ):
        self.deck = deck

    def create_environment(self) -> GameEnvironment:
        return BalatroEnvironment(
            self.deck
        )

    def get_state(
        self,
        environment: GameEnvironment
    ) -> GameState:
        return environment.get_state()

    def get_actions(
        self,
        environment: GameEnvironment
    ) -> list[Action]:
        return environment.get_actions()
