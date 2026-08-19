from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.state import BalatroState
from games.balatro.strategy import BalatroStrategyTracker
from games.balatro.strategy_catalog import UNIVERSAL_BALATRO_STRATEGIES


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = 6
    state.jokers = [JollyJoker()]
    return state


def _tracker() -> BalatroStrategyTracker:
    return BalatroStrategyTracker(
        UNIVERSAL_BALATRO_STRATEGIES,
        modifier_provider=lambda state: (
            default_balatro_playbooks().for_state(state).strategy_modifiers()
        ),
    )


def _policy(state: BalatroState) -> StrategyAwareLiveHandActionPolicy:
    tracker = _tracker()
    assert tracker.observe(state).active_strategy_id == "pair"
    return StrategyAwareLiveHandActionPolicy(strategy_tracker=tracker)


def _pair_action() -> BalatroAction:
    return BalatroAction(
        PLAY_CARDS,
        [
            BalatroCard("A", "Spades"),
            BalatroCard("A", "Hearts"),
        ],
    )


def _high_card_action() -> BalatroAction:
    return BalatroAction(
        PLAY_CARDS,
        [
            BalatroCard("A", "Spades"),
            BalatroCard("K", "Hearts"),
        ],
    )


def _plan(
    action: BalatroAction,
    *,
    clear_probability: float,
    exact: bool = True,
    expected_hands_remaining: float = 2.0,
    expected_discards_remaining: float = 2.0,
    expected_progress: float = 100.0,
    expected_score: float = 100.0,
) -> LiveBlindPlan:
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=clear_probability,
            expected_progress=expected_progress,
            expected_score=expected_score,
            expected_hands_remaining=expected_hands_remaining,
            expected_discards_remaining=expected_discards_remaining,
        ),
        horizon=2,
        exact=exact,
        candidate_count=2,
    )


def _select(
    policy: StrategyAwareLiveHandActionPolicy,
    state: BalatroState,
    *plans: LiveBlindPlan,
) -> LiveBlindPlan:
    policy._ranking_state = state
    try:
        selected = policy._select_clear_path(plans)
        assert selected is not None
        return selected
    finally:
        policy._ranking_state = None


def test_d1_guaranteed_clear_overrides_dominant_strategy_pursuit():
    state = _state()
    policy = _policy(state)
    pair = _plan(
        _pair_action(),
        clear_probability=0.99,
        expected_hands_remaining=3.0,
    )
    guaranteed_high_card = _plan(
        _high_card_action(),
        clear_probability=1.0,
        expected_hands_remaining=2.0,
    )

    selected = _select(policy, state, pair, guaranteed_high_card)

    assert selected is guaranteed_high_card


def test_d1_prefers_dominant_strategy_between_equally_efficient_guaranteed_clears():
    state = _state()
    policy = _policy(state)
    pair = _plan(
        _pair_action(),
        clear_probability=1.0,
        expected_hands_remaining=3.0,
    )
    high_card = _plan(
        _high_card_action(),
        clear_probability=1.0,
        expected_hands_remaining=3.0,
    )

    selected = _select(policy, state, pair, high_card)

    assert selected is pair


def test_d1_hand_efficiency_stays_above_strategy_among_guaranteed_clears():
    state = _state()
    policy = _policy(state)
    pair = _plan(
        _pair_action(),
        clear_probability=1.0,
        expected_hands_remaining=2.0,
    )
    more_efficient_high_card = _plan(
        _high_card_action(),
        clear_probability=1.0,
        expected_hands_remaining=3.0,
    )

    selected = _select(policy, state, pair, more_efficient_high_card)

    assert selected is more_efficient_high_card


def test_d1_held_steel_value_stays_above_strategy_fit_for_equal_clears():
    state = _state()
    steel_ace = BalatroCard("A", "Spades", enhancement="Steel")
    plain_ace = BalatroCard("A", "Hearts")
    king = BalatroCard("K", "Clubs")
    queen = BalatroCard("Q", "Diamonds")
    state.hand = [steel_ace, plain_ace, king, queen]
    policy = _policy(state)
    aligned_pair = _plan(
        BalatroAction(PLAY_CARDS, [steel_ace, plain_ace]),
        clear_probability=1.0,
        expected_hands_remaining=3.0,
    )
    preserve_steel = _plan(
        BalatroAction(PLAY_CARDS, [king, queen]),
        clear_probability=1.0,
        expected_hands_remaining=3.0,
    )

    selected = _select(policy, state, aligned_pair, preserve_steel)

    assert selected is preserve_steel


def test_d1_discard_shaping_preserves_dominant_pair_structure():
    state = _state()
    ace_spades = BalatroCard("A", "Spades")
    ace_hearts = BalatroCard("A", "Hearts")
    king = BalatroCard("K", "Clubs")
    queen = BalatroCard("Q", "Diamonds")
    state.hand = [ace_spades, ace_hearts, king, queen]
    policy = _policy(state)

    preserve_pair = BalatroAction(DISCARD_CARDS, [king, queen])
    break_pair = BalatroAction(DISCARD_CARDS, [ace_hearts, king])

    preserve_fit, _ = policy._strategy_fit(state, preserve_pair)
    break_fit, _ = policy._strategy_fit(state, break_pair)

    assert preserve_fit > break_fit


def test_d1_discard_shaping_inherits_parent_hand_from_active_leaf():
    state = BalatroState()
    state.ante = 6
    ace_spades = BalatroCard("A", "Spades")
    ace_hearts = BalatroCard("A", "Hearts")
    king = BalatroCard("K", "Clubs")
    queen = BalatroCard("Q", "Diamonds")
    state.hand = [ace_spades, ace_hearts, king, queen]

    tracker = SimpleNamespace(
        definitions={"pair_leaf": SimpleNamespace(name="Pair Leaf")},
        observe=lambda current: SimpleNamespace(active_strategy_id="pair_leaf"),
        primary_hands_for=lambda strategy_id: ("PAIR",),
        effectiveness=lambda current, strategy_id: 1.0,
    )
    policy = StrategyAwareLiveHandActionPolicy(strategy_tracker=tracker)

    preserve_fit, _ = policy._strategy_fit(
        state,
        BalatroAction(DISCARD_CARDS, [king, queen]),
    )
    break_fit, _ = policy._strategy_fit(
        state,
        BalatroAction(DISCARD_CARDS, [ace_hearts, king]),
    )

    assert preserve_fit > break_fit
