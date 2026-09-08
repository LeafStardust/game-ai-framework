from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.cerulean_bell_d1_legality_policy import (
    _cerulean_future_forced_branches,
)
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _cerulean_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.boss_name = "Cerulean Bell"
    state.blind = Blind(BlindType.BOSS, 100_000)
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.hand_size = 5
    state.hand = [
        BalatroCard("A", "Spades", live_id=1, forced_selection=True),
        BalatroCard("K", "Hearts", live_id=2),
        BalatroCard("9", "Clubs", live_id=3),
        BalatroCard("6", "Diamonds", live_id=4),
        BalatroCard("2", "Spades", live_id=5),
    ]
    return state


def test_cerulean_forced_card_is_present_in_every_d1_play_and_discard_candidate():
    state = _cerulean_state()
    forced = state.hand[0]
    planner = D1LiveBlindClearPlanner(
        play_width=6,
        discard_width=5,
        child_play_width=4,
        child_discard_width=5,
        horizon=2,
    )

    actions = planner._candidate_actions(state, allow_discards=True)
    controlled = [
        action
        for action in actions
        if action.name in {PLAY_CARDS, DISCARD_CARDS}
    ]

    assert any(action.name == PLAY_CARDS for action in controlled)
    assert any(action.name == DISCARD_CARDS for action in controlled)
    assert all(forced in action.cards for action in controlled)


def test_cerulean_child_discard_candidates_are_filtered_by_same_forced_card_rule():
    state = _cerulean_state()
    forced = state.hand[0]
    planner = D1LiveBlindClearPlanner(
        play_width=4,
        discard_width=5,
        child_play_width=4,
        child_discard_width=5,
        horizon=2,
    )

    # One consumed node makes the planner build its bounded recursive child beam
    # instead of the exhaustive root beam.
    planner.nodes_evaluated = 1
    actions = planner._candidate_actions(state, allow_discards=True)
    discards = [action for action in actions if action.name == DISCARD_CARDS]

    assert discards
    assert all(forced in action.cards for action in discards)


def test_cerulean_future_hand_branches_uniformly_over_each_possible_forced_card():
    state = _cerulean_state()
    for card in state.hand:
        card.forced_selection = False

    branches = _cerulean_future_forced_branches(state)

    assert branches is not None
    assert len(branches) == len(state.hand)
    assert sum(probability for probability, _ in branches) == 1.0
    assert all(probability == 1.0 / len(state.hand) for probability, _ in branches)

    selected_ids = []
    for _, branch in branches:
        forced = [card for card in branch.hand if card.forced_selection]
        assert len(forced) == 1
        selected_ids.append(forced[0].live_id)
    assert set(selected_ids) == {card.live_id for card in state.hand}


def test_cerulean_future_brancher_does_not_reroll_observed_forced_card():
    state = _cerulean_state()

    assert _cerulean_future_forced_branches(state) is None


def test_chicot_disables_cerulean_future_forced_branching():
    state = _cerulean_state()
    for card in state.hand:
        card.forced_selection = False
    state.jokers = [ChicotJoker()]

    assert _cerulean_future_forced_branches(state) is None


def test_cerulean_unselected_future_hand_is_exact_after_d1_forced_card_branching():
    state = _cerulean_state()
    for card in state.hand:
        card.forced_selection = False
    state.hands_remaining = 1
    state.discards_remaining = 0

    planner = D1LiveBlindClearPlanner(
        play_width=3,
        discard_width=0,
        child_play_width=3,
        child_discard_width=0,
        horizon=1,
    )
    planner.nodes_evaluated = 1

    _, exact = planner._best_value(state, 1)

    assert exact is True
