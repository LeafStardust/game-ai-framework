from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.public_observation import public_observation_state
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.state import BalatroState


def _joker(joker_type, live_id):
    joker = joker_type()
    joker.live_id = live_id
    joker.area_index = live_id + 10
    return joker


def _state(order):
    state = BalatroState()
    state.boss_name = "Amber Acorn"
    state.blind = Blind(BlindType.BOSS, 100000)
    state.phase = "SELECTING_HAND"
    state.jokers = list(order)
    return state


def _classes(state):
    return [type(joker).__name__ for joker in state.jokers]


def test_env_r2_active_amber_hides_identity_to_physical_position_mapping():
    first = _joker(FlatMultJoker, 1)
    second = _joker(JollyJoker, 2)
    third = _joker(SlyJoker, 3)

    left = public_observation_state(_state([third, first, second]))
    right = public_observation_state(_state([second, third, first]))

    assert _classes(left) == _classes(right)
    assert _classes(left) == ["FlatMultJoker", "JollyJoker", "SlyJoker"]
    assert [getattr(joker, "live_id", None) for joker in left.jokers] == [None, None, None]
    assert [getattr(joker, "area_index", None) for joker in left.jokers] == [None, None, None]


def test_env_r2_active_amber_observation_does_not_mutate_hidden_source_order_or_ids():
    first = _joker(FlatMultJoker, 1)
    second = _joker(JollyJoker, 2)
    source = _state([second, first])

    observation = public_observation_state(source)

    assert source.jokers == [second, first]
    assert [joker.live_id for joker in source.jokers] == [2, 1]
    assert observation.jokers[0] is not source.jokers[1]
    assert observation.jokers[1] is not source.jokers[0]


def test_env_r2_amber_blind_select_still_exposes_pre_flip_visible_order():
    first = _joker(FlatMultJoker, 1)
    second = _joker(JollyJoker, 2)
    state = _state([second, first])
    state.phase = "BLIND_SELECT"

    observation = public_observation_state(state)

    assert _classes(observation) == ["JollyJoker", "FlatMultJoker"]
    assert [joker.live_id for joker in observation.jokers] == [2, 1]


def test_env_r2_disabling_amber_restores_visible_current_physical_order():
    first = _joker(FlatMultJoker, 1)
    second = _joker(JollyJoker, 2)
    state = _state([second, first])
    state.blind.disabled = True

    observation = public_observation_state(state)

    assert _classes(observation) == ["JollyJoker", "FlatMultJoker"]
    assert [joker.live_id for joker in observation.jokers] == [2, 1]
