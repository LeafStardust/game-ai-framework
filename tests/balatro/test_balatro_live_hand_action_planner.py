from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine
from games.balatro.state import BalatroState


def _live_like_state():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("K", "Clubs", live_id=0),
        BalatroCard("10", "Diamonds", live_id=1),
        BalatroCard("9", "Clubs", live_id=2),
        BalatroCard("6", "Diamonds", live_id=3),
        BalatroCard("4", "Spades", live_id=4),
        BalatroCard("4", "Hearts", live_id=5),
        BalatroCard("3", "Clubs", live_id=6),
        BalatroCard("2", "Clubs", live_id=7),
    ]
    state.deck = [
        BalatroCard("A", "Clubs"),
        BalatroCard("Q", "Clubs"),
        BalatroCard("J", "Hearts"),
        BalatroCard("8", "Spades"),
        BalatroCard("7", "Diamonds"),
    ]
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 4
    state.blind = Blind(BlindType.SMALL, 300)
    state.jokers = []
    return state


def _flush_draw_state():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("K", "Clubs", live_id=0),
        BalatroCard("9", "Clubs", live_id=1),
        BalatroCard("7", "Clubs", live_id=2),
        BalatroCard("2", "Clubs", live_id=3),
        BalatroCard("Q", "Diamonds", live_id=4),
        BalatroCard("10", "Hearts", live_id=5),
        BalatroCard("6", "Spades", live_id=6),
        BalatroCard("4", "Hearts", live_id=7),
    ]
    state.deck = []
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 4
    state.blind = Blind(BlindType.SMALL, 300)
    state.jokers = []
    return state


def _guaranteed_clear_state():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("K", "Spades", live_id=0),
        BalatroCard("K", "Clubs", live_id=1),
        BalatroCard("K", "Diamonds", live_id=2),
        BalatroCard("10", "Clubs", live_id=3),
        BalatroCard("10", "Diamonds", live_id=4),
        BalatroCard("9", "Clubs", live_id=5),
        BalatroCard("3", "Clubs", live_id=6),
        BalatroCard("2", "Clubs", live_id=7),
    ]
    state.deck = []
    state.score = 36
    state.hands_remaining = 3
    state.discards_remaining = 4
    state.blind = Blind(BlindType.SMALL, 300)
    state.jokers = []
    return state


def test_d1_decision_engine_defaults_to_diversity_aware_planner():
    engine = LiveHandActionDecisionEngine()

    assert isinstance(engine.planner, D1LiveBlindClearPlanner)


def test_d1_beam_remains_bounded_by_configured_widths():
    state = _live_like_state()
    planner = D1LiveBlindClearPlanner(play_width=6, discard_width=4, horizon=2)

    actions = planner._candidate_actions(state, allow_discards=True)

    assert sum(action.name == PLAY_CARDS for action in actions) == 6
    assert sum(action.name == DISCARD_CARDS for action in actions) == 4


def test_d1_play_beam_preserves_pair_plus_trash_cycle_sizes():
    state = _live_like_state()
    planner = D1LiveBlindClearPlanner(play_width=6, discard_width=4, horizon=2)

    actions = planner._candidate_actions(state, allow_discards=False)
    plays = [action for action in actions if action.name == PLAY_CARDS]

    pair_core_ids = {id(state.hand[4]), id(state.hand[5])}
    represented_sizes = set()
    for action in plays:
        hand = planner.evaluator.hand_evaluator.evaluate(action.cards)
        scoring = planner.evaluator.scorer.scoring_cards(hand, action.cards)
        if {id(card) for card in scoring} == pair_core_ids:
            represented_sizes.add(len(action.cards))

    assert {2, 3, 4, 5}.issubset(represented_sizes)


def test_d1_discard_beam_preserves_distinct_redraw_sizes():
    state = _live_like_state()
    planner = D1LiveBlindClearPlanner(play_width=6, discard_width=4, horizon=2)

    actions = planner._candidate_actions(state, allow_discards=True)
    discards = [action for action in actions if action.name == DISCARD_CARDS]

    assert {len(action.cards) for action in discards} == {1, 2, 3, 4}


def test_four_card_discard_represents_best_retained_structure_for_that_size():
    state = _live_like_state()
    planner = D1LiveBlindClearPlanner(play_width=6, discard_width=4, horizon=2)

    actions = planner._candidate_actions(state, allow_discards=True)
    selected = next(
        action
        for action in actions
        if action.name == DISCARD_CARDS and len(action.cards) == 4
    )
    all_four_card_discards = [
        action
        for action in planner.action_generator.generate_discard_actions(state)
        if len(action.cards) == 4
    ]

    assert planner._discard_priority(state, selected) == max(
        planner._discard_priority(state, action)
        for action in all_four_card_discards
    )


def test_four_card_discard_preserves_four_club_flush_when_flush_is_best_structure():
    state = _flush_draw_state()
    planner = D1LiveBlindClearPlanner(play_width=6, discard_width=4, horizon=2)

    actions = planner._candidate_actions(state, allow_discards=True)
    four_card = next(
        action
        for action in actions
        if action.name == DISCARD_CARDS and len(action.cards) == 4
    )
    discarded_ids = {id(card) for card in four_card.cards}
    kept = [card for card in state.hand if id(card) not in discarded_ids]

    assert sum(1 for card in kept if card.suit == "Clubs") == 4


def test_guaranteed_immediate_clear_suppresses_discard_branches():
    state = _guaranteed_clear_state()
    planner = D1LiveBlindClearPlanner(play_width=6, discard_width=4, horizon=2)

    actions = planner._candidate_actions(state, allow_discards=True)

    assert actions
    assert all(action.name == PLAY_CARDS for action in actions)
    assert all(planner.evaluator.project_play(state, action).clears_blind for action in actions)

    best = actions[0]
    selected_ids = {id(card) for card in best.cards}
    full_house_ids = {id(card) for card in state.hand[:5]}
    assert selected_ids == full_house_ids


def test_root_shortlist_prefers_plain_pair_card_over_equivalent_steel_card():
    five_spades = BalatroCard("5", "Spades", live_id=1)
    five_diamonds = BalatroCard("5", "Diamonds", live_id=2)
    plain_two_a = BalatroCard("2", "Hearts", live_id=3)
    steel_two = BalatroCard("2", "Clubs", enhancement="Steel", live_id=4)
    plain_two_b = BalatroCard("2", "Diamonds", live_id=5)
    planner = D1LiveBlindClearPlanner(play_width=6, discard_width=4, horizon=2)
    plain = BalatroAction(
        PLAY_CARDS,
        cards=[five_spades, five_diamonds, plain_two_a, plain_two_b],
    )
    wastes_steel = BalatroAction(
        PLAY_CARDS,
        cards=[five_spades, five_diamonds, plain_two_a, steel_two],
    )

    assert (
        planner._direct_child_play_priority(plain)
        > planner._direct_child_play_priority(wastes_steel)
    )
