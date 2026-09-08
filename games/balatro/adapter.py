from framework.core.environment import GameEnvironment
from framework.core.state import GameState
from framework.core.action import Action

from games.adapter import GameAdapter
from games.balatro.decks import BASE_DECK, BalatroDeck
from games.balatro.stake_environment import BalatroStakeEnvironment
from games.balatro.stakes import WHITE_STAKE, BalatroStake


class BalatroAdapter(GameAdapter):

    def __init__(
        self,
        deck: BalatroDeck = BASE_DECK,
        stake: BalatroStake = WHITE_STAKE
    ):
        self.deck = deck
        self.stake = stake

    def create_environment(self) -> GameEnvironment:
        return BalatroStakeEnvironment(
            self.deck,
            self.stake
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
