from framework.core.state import GameState

from games.balatro.card import BalatroCard
from games.balatro.blinds.blind import Blind, BlindType


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
        self.blind_score: int = 0

        self.blind = Blind(
            BlindType.SMALL,
            requirement=300
        )

        # Cards
        self.hand: list[BalatroCard] = []
        self.deck_size: int = 52
        self.discards_remaining: int = 3

        # Jokers and upgrades
        self.jokers: list = []
        self.vouchers: list = []

        # Current decision context
        self.phase: str = "ROUND_START"


    @property
    def blind_requirement(self):
        return self.blind.requirement


    @blind_requirement.setter
    def blind_requirement(self, value):
        self.blind.requirement = value


    def copy(self):

        new_state = BalatroState()

        new_state.money = self.money

        new_state.ante = self.ante
        new_state.round = self.round

        new_state.score = self.score

        new_state.blind_score = self.blind_score
        new_state.blind = self.blind

        new_state.hand = self.hand.copy()
        new_state.deck_size = self.deck_size

        new_state.jokers = self.jokers.copy()
        new_state.vouchers = self.vouchers.copy()

        new_state.phase = self.phase

        return new_state