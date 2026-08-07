from framework.core.state import GameState
from games.balatro.card import BalatroCard


class BalatroState(GameState):
    """
    Represents the observable state of a Balatro run.
    """

    def __init__(self):

        # Economy
        self.money: int = 0

        # Run progression
        self.ante: int = 1
        self.round: int = 1

        # Blind scoring
        self.score: int = 0
        self.blind_requirement: int = 0

        # Cards
        self.hand: list[BalatroCard] = []
        self.deck_size: int = 52
        self.discards_remaining: int = 3

        # Jokers and upgrades
        self.jokers: list = []
        self.vouchers: list = []

        # Current decision context
        self.phase: str = "ROUND_START"


    def copy(self):

        new_state = BalatroState()

        new_state.money = self.money

        new_state.ante = self.ante
        new_state.round = self.round

        new_state.score = self.score

        new_state.hand = self.hand.copy()
        new_state.deck_size = self.deck_size

        new_state.jokers = self.jokers.copy()
        new_state.vouchers = self.vouchers.copy()

        new_state.phase = self.phase

        return new_state