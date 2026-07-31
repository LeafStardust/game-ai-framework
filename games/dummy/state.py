from framework.core.state import GameState


class DummyState(GameState):
    """
    Represents the current state of the dummy environment.
    """

    def __init__(self, value=0):
        self.value = value