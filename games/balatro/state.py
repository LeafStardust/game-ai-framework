from framework.core.state import GameState

from games.balatro.card import BalatroCard


class BalatroState(GameState):

    def __init__(self):

        self.money: int = 0

        self.ante: int = 1
        self.round: int = 1

        self.score: int = 0
        self.blind_score: int = 0

        self.blind = None
        self.boss_name: str | None = None

        self.hand: list[BalatroCard] = []
        self.deck_size: int = 52
        self.discards_remaining: int = 3

        self.jokers: list = []
        self.vouchers: list = []

        self.phase: str = "ROUND_START"


    @property
    def blind_requirement(self):

        if self.blind is None:
            return 0

        return self.blind.requirement


    @blind_requirement.setter
    def blind_requirement(
        self,
        value
    ):

        if self.blind is not None:
            self.blind.requirement = value


    def copy(self):

        new_state = BalatroState()

        new_state.money = self.money

        new_state.ante = self.ante
        new_state.round = self.round

        new_state.score = self.score
        new_state.blind_score = self.blind_score

        if self.blind is not None:
            new_state.blind = self.blind.copy()

        new_state.boss_name = self.boss_name

        new_state.hand = self.hand.copy()
        new_state.deck_size = self.deck_size

        new_state.jokers = self.jokers.copy()
        new_state.vouchers = self.vouchers.copy()

        new_state.phase = self.phase

        return new_state