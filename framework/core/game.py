from framework.core.environment import GameEnvironment
from games.adapter import GameAdapter


class Game:
    """
    Represents a playable game instance.
    """

    def __init__(
        self,
        adapter: GameAdapter
    ):
        self.adapter = adapter
        self.environment: GameEnvironment = (
            adapter.create_environment()
        )