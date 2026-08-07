from framework.core.environment import GameEnvironment


class GameContext:
    """
    Provides runtime game dependencies to decision systems.
    """

    def __init__(
        self,
        environment: GameEnvironment
    ):
        self.environment = environment