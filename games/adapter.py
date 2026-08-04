from framework.core.environment import GameEnvironment


class GameAdapter:
    """
    Base interface for connecting games to the framework.
    """

    def create_environment(self) -> GameEnvironment:
        raise NotImplementedError