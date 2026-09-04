import pytest

from games.balatro.env.joker_order import (
    JokerOrderError,
    JokerOrderState,
    derive_joker_creation_order,
)
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.sly_joker import SlyJoker


def _joker(joker_type, live_id=None):
    joker = joker_type()
    if live_id is not None:
        joker.live_id = live_id
    return joker


def test_env_r2_joker_creation_order_uses_unique_live_sort_ids():
    first = _joker(FlatMultJoker, 4)
    second = _joker(JollyJoker, 12)
    third = _joker(SlyJoker, 7)
    public = [second, first, third]

    order = derive_joker_creation_order(public)

    assert order == [first, third, second]
    owner = JokerOrderState.from_public(public)
    assert owner is not None
    assert owner.creation_order == [first, third, second]
    assert owner.physical_order == public
    owner.validate_against(public)


def test_env_r2_joker_creation_order_empty_and_single_are_intrinsically_exact():
    assert derive_joker_creation_order([]) == []

    joker = _joker(FlatMultJoker)
    assert derive_joker_creation_order([joker]) == [joker]
    owner = JokerOrderState.from_public([joker])
    assert owner is not None
    owner.validate_against([joker])


@pytest.mark.parametrize("ids", [(1, None), (1, "2"), (1, True), (1, 1)])
def test_env_r2_multi_joker_unknown_or_duplicate_creation_ids_fail_closed(ids):
    first = _joker(FlatMultJoker)
    second = _joker(JollyJoker)
    first.live_id = ids[0]
    second.live_id = ids[1]

    assert derive_joker_creation_order([first, second]) is None
    assert JokerOrderState.from_public([first, second]) is None


def test_env_r2_joker_order_tracks_exact_acquisition_and_removal():
    first = _joker(FlatMultJoker)
    owner = JokerOrderState.from_public([first])
    assert owner is not None

    second = _joker(JollyJoker)
    owner.acquire(second, [first])
    owned = [first, second]
    owner.validate_against(owned)
    assert owner.creation_order == owned
    assert owner.physical_order == owned

    owner.remove(first, owned)
    owned = [second]
    owner.validate_against(owned)
    assert owner.creation_order == [second]
    assert owner.physical_order == [second]


def test_env_r2_joker_order_retains_creation_order_while_physical_order_changes():
    first = _joker(FlatMultJoker, 1)
    second = _joker(JollyJoker, 2)
    third = _joker(SlyJoker, 3)
    owned = [first, second, third]
    owner = JokerOrderState.from_public(owned)
    assert owner is not None

    owner.set_physical_order([third, first, second], owned)

    assert owner.creation_order == owned
    assert owner.physical_order == [third, first, second]
    owner.validate_against(owned)


def test_env_r2_joker_order_rejects_stale_or_non_permutation_state():
    first = _joker(FlatMultJoker, 1)
    second = _joker(JollyJoker, 2)
    owner = JokerOrderState.from_public([first, second])
    assert owner is not None

    with pytest.raises(JokerOrderError, match="permutation"):
        owner.set_physical_order([first], [first, second])

    with pytest.raises(JokerOrderError, match="stale"):
        owner.validate_against([first])
