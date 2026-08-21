from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.state import BalatroState


class CountingTracker:
    def __init__(self):
        self.hand_fit_calls = 0
        self.relationship_calls = 0

    def _relationships_for(self, joker, *, kind):
        self.relationship_calls += 1
        return {}

    def hand_fit(self, state, hand_type):
        self.hand_fit_calls += 1
        return 0.25, (f"fit:{hand_type}",)

    def effectiveness(self, state, strategy_id):
        return 1.0

    def primary_hands_for(self, strategy_id):
        return ()


def _pair(rank, suit_a, suit_b):
    return BalatroAction(
        PLAY_CARDS,
        cards=[BalatroCard(rank, suit_a), BalatroCard(rank, suit_b)],
    )


def test_equivalent_play_hand_types_reuse_one_strategy_fit_within_checkpoint():
    tracker = CountingTracker()
    policy = StrategyAwareLiveHandActionPolicy(strategy_tracker=tracker)
    state = BalatroState()
    state.jokers = []

    first = _pair("8", "Hearts", "Spades")
    second = _pair("K", "Clubs", "Diamonds")

    policy._checkpoint_strategy_fit_cache = {}
    policy._checkpoint_owned_hand_weights = None
    policy._checkpoint_strategy_fit_state_id = id(state)
    try:
        one = policy._strategy_fit(state, first)
        two = policy._strategy_fit(state, second)
    finally:
        policy._checkpoint_strategy_fit_cache = None
        policy._checkpoint_owned_hand_weights = None
        policy._checkpoint_strategy_fit_state_id = None

    assert one == two
    assert tracker.hand_fit_calls == 1


def test_cache_is_not_reused_across_state_identity():
    tracker = CountingTracker()
    policy = StrategyAwareLiveHandActionPolicy(strategy_tracker=tracker)
    first_state = BalatroState()
    second_state = BalatroState()
    action = _pair("8", "Hearts", "Spades")

    policy._checkpoint_strategy_fit_cache = {}
    policy._checkpoint_owned_hand_weights = None
    policy._checkpoint_strategy_fit_state_id = id(first_state)
    policy._strategy_fit(first_state, action)
    policy._strategy_fit(second_state, action)

    assert tracker.hand_fit_calls == 2
