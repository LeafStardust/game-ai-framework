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

        self.deck: list[BalatroCard] = self._create_deck()
        self.hand: list[BalatroCard] = []
        self.discard_pile: list[BalatroCard] = []

        self.discards_remaining: int = 3

        self.jokers: list = []
        self.consumables: list = []
        self.consumable_slots = 2
        self.hand_levels = {
            "HIGH_CARD": 1,
            "PAIR": 1,
            "TWO_PAIR": 1,
            "THREE_OF_A_KIND": 1,
            "STRAIGHT": 1,
            "FLUSH": 1,
            "FULL_HOUSE": 1,
            "FOUR_OF_A_KIND": 1,
            "STRAIGHT_FLUSH": 1
        }
        self.vouchers: list = []

        self.phase: str = "ROUND_START"

        self.glass_cards_destroyed: int = 0

    @property
    def deck_size(self) -> int:

        return len(self.deck)


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


    def _create_deck(self):

        ranks = [
            "2", "3", "4", "5", "6",
            "7", "8", "9", "10",
            "J", "Q", "K", "A"
        ]

        suits = [
            "Hearts",
            "Diamonds",
            "Clubs",
            "Spades"
        ]

        return [
            BalatroCard(rank, suit)
            for rank in ranks
            for suit in suits
        ]


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

        new_state.deck = self.deck.copy()
        new_state.hand = self.hand.copy()
        new_state.discard_pile = self.discard_pile.copy()

        new_state.discards_remaining = self.discards_remaining

        new_state.jokers = self.jokers.copy()
        new_state.consumables = self.consumables.copy()
        new_state.consumable_slots = self.consumable_slots
        new_state.hand_levels = self.hand_levels.copy()
        new_state.vouchers = self.vouchers.copy()

        new_state.phase = self.phase

        new_state.glass_cards_destroyed = self.glass_cards_destroyed

        return new_state