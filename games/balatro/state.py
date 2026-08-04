from framework.core.state import GameState


class BalatroState(GameState):
    """
    Represents the current state of a Balatro run.
    """

    def __init__(
        self
    ):
        self.money: int = 0
        self.hand_size: int = 8
        self.current_round: int = 1
        self.score: int = 0

        self.hand: list = []
        self.jokers: list = []
        self.deck: list = []