from __future__ import annotations

import games.balatro  # initialize package-level live authorities

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import create_small_blind
from games.balatro.card import BalatroCard
from games.balatro.live.hand_action_planner_core import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _state(*, requirement: int = 5) -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.blind = create_small_blind(requirement)
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.consumable_slots = 1
    state.consumables = []
    state.deck = []
    return state


def test_blue_seal_held_on_clear_adds_capacity_valid_round_end_resource() -> None:
    state = _state()
    scorer = BalatroCard("2", "Clubs", live_id="scorer")
    blue = BalatroCard("3", "Hearts", seal="Blue", live_id="blue")
    state.hand = [scorer, blue]

    action = BalatroAction(PLAY_CARDS, cards=[scorer])
    estimate = D1LiveBlindClearPlanner(horizon=1)._estimate_action(state, action, 1)

    assert estimate.value.clear_probability == 1.0
    assert estimate.value.expected_consumables == 1.0


def test_blue_seal_played_on_clear_does_not_create_round_end_resource() -> None:
    state = _state()
    scorer = BalatroCard("2", "Clubs", live_id="scorer")
    blue = BalatroCard("3", "Hearts", seal="Blue", live_id="blue")
    state.hand = [scorer, blue]

    action = BalatroAction(PLAY_CARDS, cards=[scorer, blue])
    estimate = D1LiveBlindClearPlanner(horizon=1)._estimate_action(state, action, 1)

    assert estimate.value.clear_probability == 1.0
    assert estimate.value.expected_consumables == 0.0


def test_blue_seal_does_not_overfill_consumable_capacity() -> None:
    state = _state()
    state.consumables = [object()]
    scorer = BalatroCard("2", "Clubs", live_id="scorer")
    blue = BalatroCard("3", "Hearts", seal="Blue", live_id="blue")
    state.hand = [scorer, blue]

    action = BalatroAction(PLAY_CARDS, cards=[scorer])
    estimate = D1LiveBlindClearPlanner(horizon=1)._estimate_action(state, action, 1)

    # The existing held consumable remains in terminal value, but no impossible
    # second consumable is credited for the Blue Seal when capacity is full.
    assert estimate.value.expected_consumables == 1.0


def test_debuffed_blue_seal_has_no_round_end_resource_value() -> None:
    state = _state()
    scorer = BalatroCard("2", "Clubs", live_id="scorer")
    blue = BalatroCard(
        "3",
        "Hearts",
        seal="Blue",
        live_id="blue",
        debuffed=True,
    )
    state.hand = [scorer, blue]

    action = BalatroAction(PLAY_CARDS, cards=[scorer])
    estimate = D1LiveBlindClearPlanner(horizon=1)._estimate_action(state, action, 1)

    assert estimate.value.expected_consumables == 0.0


def test_gold_card_is_preserved_only_as_final_mechanical_tie_break() -> None:
    state = _state()
    plain = BalatroCard("2", "Clubs", live_id="plain")
    gold = BalatroCard("2", "Clubs", enhancement="Gold", live_id="gold")
    state.hand = [plain, gold]

    planner = D1LiveBlindClearPlanner(horizon=1)
    play_plain = BalatroAction(PLAY_CARDS, cards=[plain])
    play_gold = BalatroAction(PLAY_CARDS, cards=[gold])

    assert planner._play_priority(state, play_plain) > planner._play_priority(
        state,
        play_gold,
    )


def test_gold_preservation_does_not_override_stronger_scoring_play() -> None:
    state = _state(requirement=15)
    low_plain = BalatroCard("2", "Clubs", live_id="plain")
    gold_ace = BalatroCard("A", "Spades", enhancement="Gold", live_id="gold")
    state.hand = [low_plain, gold_ace]

    planner = D1LiveBlindClearPlanner(horizon=1)
    play_low = BalatroAction(PLAY_CARDS, cards=[low_plain])
    play_gold_ace = BalatroAction(PLAY_CARDS, cards=[gold_ace])

    assert planner._play_priority(state, play_gold_ace) > planner._play_priority(
        state,
        play_low,
    )


def test_gold_card_is_not_overplayed_as_non_scoring_pair_kicker_on_clear() -> None:
    state = _state()
    left = BalatroCard("2", "Clubs", live_id="left")
    right = BalatroCard("2", "Hearts", live_id="right")
    gold = BalatroCard("K", "Spades", enhancement="Gold", live_id="gold")
    state.hand = [left, right, gold]

    planner = D1LiveBlindClearPlanner(horizon=1)
    pair_only = BalatroAction(PLAY_CARDS, cards=[left, right])
    pair_with_gold = BalatroAction(PLAY_CARDS, cards=[left, right, gold])

    assert planner._play_priority(state, pair_only) > planner._play_priority(
        state,
        pair_with_gold,
    )


def test_blue_seal_is_not_overplayed_as_non_scoring_pair_kicker_on_clear() -> None:
    state = _state()
    left = BalatroCard("2", "Clubs", live_id="left")
    right = BalatroCard("2", "Hearts", live_id="right")
    blue = BalatroCard("K", "Spades", seal="Blue", live_id="blue")
    state.hand = [left, right, blue]

    planner = D1LiveBlindClearPlanner(horizon=1)
    pair_only = BalatroAction(PLAY_CARDS, cards=[left, right])
    pair_with_blue = BalatroAction(PLAY_CARDS, cards=[left, right, blue])

    assert planner._play_priority(state, pair_only) > planner._play_priority(
        state,
        pair_with_blue,
    )


def test_steel_card_is_not_overplayed_as_non_scoring_pair_kicker() -> None:
    state = _state(requirement=20)
    left = BalatroCard("2", "Clubs", live_id="left")
    right = BalatroCard("2", "Hearts", live_id="right")
    steel = BalatroCard("K", "Spades", enhancement="Steel", live_id="steel")
    state.hand = [left, right, steel]

    planner = D1LiveBlindClearPlanner(horizon=1)
    pair_only = BalatroAction(PLAY_CARDS, cards=[left, right])
    pair_with_steel = BalatroAction(PLAY_CARDS, cards=[left, right, steel])

    assert planner._play_priority(state, pair_only) > planner._play_priority(
        state,
        pair_with_steel,
    )


def test_low_value_non_scoring_card_remains_available_as_cycling_variant() -> None:
    state = _state(requirement=10_000)
    left = BalatroCard("2", "Clubs", live_id="left")
    right = BalatroCard("2", "Hearts", live_id="right")
    dead = BalatroCard("3", "Spades", live_id="dead")
    state.hand = [left, right, dead]

    planner = D1LiveBlindClearPlanner(horizon=1, play_width=2)
    pair_only = BalatroAction(PLAY_CARDS, cards=[left, right])
    pair_with_dead = BalatroAction(PLAY_CARDS, cards=[left, right, dead])

    beam = planner._diverse_play_beam(state, [pair_only, pair_with_dead], 2)
    identities = {planner._action_identity(action) for action in beam}

    assert planner._action_identity(pair_only) in identities
    assert planner._action_identity(pair_with_dead) in identities
