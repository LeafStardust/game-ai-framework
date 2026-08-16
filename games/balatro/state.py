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
        # Public mutable state owned by the active Blind object. The Eye records
        # accepted hand types in ``Blind.hands`` while The Mouth stores its first
        # accepted type in ``Blind.only_hand``. Keep an observation bit so an
        # empty/false live value is distinguishable from a source that never
        # exposed the fields at all.
        self.boss_blind_state_observed: bool = False
        self.boss_blind_hands: set[str] = set()
        self.boss_blind_only_hand: str | None = None
        self.deck_name: str = "BASE"
        self.stake_name: str = "WHITE"
        self.deck: list[BalatroCard] = self._create_deck()
        # ``deck`` may represent only the currently drawable composition in live
        # play. ``owned_deck`` is the optional authoritative permanent playing-card
        # composition; ``None`` means that source was not observed and callers may
        # deliberately fall back to legacy ``deck`` semantics.
        self.owned_deck: list[BalatroCard] | None = None
        self.hand: list[BalatroCard] = []
        self.hand_size: int = 8
        self.hands_remaining: int = 4
        self.discard_pile: list[BalatroCard] = []
        self.discards_remaining: int = 3
        # Public current-round discard history. ``None`` means the observation
        # source did not expose enough information to distinguish the first
        # discard from a later discard; first-discard mechanics must then fail
        # closed instead of guessing.
        self.discards_used: int | None = None
        self.jokers: list = []
        self.joker_slots: int = 5
        self.consumables: list = []
        self.shop_jokers: list = []
        self.shop_consumables: list = []
        self.shop_boosters: list = []
        self.shop_vouchers: list = []
        self.shop_active = False
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
            "STRAIGHT_FLUSH": 1,
            "FIVE_OF_A_KIND": 1,
            "FLUSH_HOUSE": 1,
            "FLUSH_FIVE": 1,
        }
        # Public run-history count for each poker hand. Live observation derives
        # this from the ordinary G.GAME.hands[*].played counters; no hidden draw or
        # RNG state is involved.
        self.hand_play_counts = {
            hand: 0
            for hand in self.hand_levels
        }
        # Public current-round history for Card Sharp and D1 child projections.
        # Live observation derives this from G.GAME.hands[*].played_this_round.
        self.round_hand_play_counts = {
            hand: 0
            for hand in self.hand_levels
        }
        self.vouchers: list = []
        self.phase: str = "ROUND_START"
        self.glass_cards_destroyed: int = 0
        self.last_played_hand: str | None = None
        # Public run history used by The Fool. Balatro stores this as the center
        # key of the last Tarot/Planet used; ``None`` means no usable history was
        # observed. This is ordinary visible run state, not RNG state.
        self.last_tarot_planet: str | None = None

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
        new_state.boss_blind_state_observed = self.boss_blind_state_observed
        new_state.boss_blind_hands = self.boss_blind_hands.copy()
        new_state.boss_blind_only_hand = self.boss_blind_only_hand
        new_state.deck_name = self.deck_name
        new_state.stake_name = self.stake_name
        new_state.deck = self.deck.copy()
        new_state.owned_deck = (
            self.owned_deck.copy()
            if self.owned_deck is not None
            else None
        )
        new_state.hand = self.hand.copy()
        new_state.hand_size = self.hand_size
        new_state.hands_remaining = self.hands_remaining
        new_state.discard_pile = self.discard_pile.copy()
        new_state.discards_remaining = self.discards_remaining
        new_state.discards_used = self.discards_used
        new_state.jokers = self.jokers.copy()
        new_state.joker_slots = self.joker_slots
        new_state.consumables = self.consumables.copy()
        new_state.shop_jokers = self.shop_jokers.copy()
        new_state.shop_consumables = self.shop_consumables.copy()
        new_state.shop_boosters = self.shop_boosters.copy()
        new_state.shop_vouchers = self.shop_vouchers.copy()
        new_state.shop_active = self.shop_active
        new_state.consumable_slots = self.consumable_slots
        new_state.hand_levels = self.hand_levels.copy()
        new_state.hand_play_counts = self.hand_play_counts.copy()
        new_state.round_hand_play_counts = self.round_hand_play_counts.copy()
        new_state.vouchers = self.vouchers.copy()
        new_state.phase = self.phase
        new_state.glass_cards_destroyed = self.glass_cards_destroyed
        new_state.last_played_hand = self.last_played_hand
        new_state.last_tarot_planet = self.last_tarot_planet

        return new_state

    def add_consumable(self, consumable) -> bool:

        if len(self.consumables) >= self.consumable_slots:
            return False

        self.consumables.append(
            consumable
        )

        return True

    def remove_consumable(self, consumable) -> bool:

        if consumable not in self.consumables:
            return False

        self.consumables.remove(
            consumable
        )

        return True
