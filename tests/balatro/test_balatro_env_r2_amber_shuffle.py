from games.balatro.env.amber_acorn import apply_amber_acorn_shuffle
from games.balatro.env.joker_order import JokerOrderState
from games.balatro.env.rng import BalatroRNG
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.jokers.wily_joker import WilyJoker


def _jokers(count=5):
    types = [FlatMultJoker, JollyJoker, SlyJoker, ZanyJoker, WilyJoker]
    values = []
    for live_id, joker_type in enumerate(types[:count], start=1):
        joker = joker_type()
        joker.live_id = live_id
        values.append(joker)
    return values


def _ids(values):
    return [joker.live_id for joker in values]


def test_env_r2_amber_three_shuffles_pin_final_creation_order_vector():
    owned = _jokers()
    order = JokerOrderState.from_public(owned)
    assert order is not None
    rng = BalatroRNG("AMBER-TEST")

    result = apply_amber_acorn_shuffle(order, rng, owned)

    assert _ids(result.order.creation_order) == [1, 2, 3, 4, 5]
    assert _ids(result.order.physical_order) == [4, 5, 2, 1, 3]
    assert result.rng.nodes["aajk"] == 0.991074513307


def test_env_r2_amber_each_pass_restarts_from_creation_order_not_previous_shuffle():
    owned = _jokers()
    order = JokerOrderState.from_public(owned)
    assert order is not None

    expected_rng = BalatroRNG("AMBER-TEST")
    expected = None
    for _ in range(3):
        expected = list(order.creation_order)
        expected_rng.shuffle_in_place(expected, "aajk")

    result = apply_amber_acorn_shuffle(order, BalatroRNG("AMBER-TEST"), owned)

    assert result.order.physical_order == expected
    assert result.rng.snapshot() == expected_rng.snapshot()


def test_env_r2_amber_zero_or_one_joker_does_not_advance_aajk_rng():
    for owned in ([], _jokers(1)):
        order = JokerOrderState.from_public(owned)
        assert order is not None
        rng = BalatroRNG("AMBER-TEST")
        before = rng.snapshot()

        result = apply_amber_acorn_shuffle(order, rng, owned)

        assert result.rng.snapshot() == before
        assert result.order.physical_order == owned


def test_env_r2_amber_shuffle_isolates_input_order_and_rng():
    owned = _jokers()
    order = JokerOrderState.from_public(owned)
    assert order is not None
    rng = BalatroRNG("AMBER-TEST")
    before_rng = rng.snapshot()
    before_physical = list(order.physical_order)

    result = apply_amber_acorn_shuffle(order, rng, owned)

    assert order.physical_order == before_physical
    assert order.creation_order == owned
    assert rng.snapshot() == before_rng
    assert result.rng.snapshot() != before_rng
    assert result.order is not order
