import pytest

from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.joker_removal import destroy_inventory_only_joker_exact
from games.balatro.env.joker_sale import (
    can_sell_joker_exact,
    sell_joker_exact,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.shop_generation_state import suppress_visible_shop_jokers_from_generation_pool
from games.balatro.env.shop_items import (
    GeneratedShopJokerItem,
    materialize_generated_shop_joker_for_acquisition,
)
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.rocket import RocketJoker
from games.balatro.jokers.vampire import VampireJoker
from games.balatro.jokers.troubadour import TroubadourJoker
from games.balatro.state import BalatroState


def _shop_run(joker=None) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 7
    selected = joker or FlatMultJoker()
    selected.sell_cost = 3
    state.jokers = [selected]
    return HeadlessRunState(public=state, seed="SELL-JOKER")


@pytest.mark.parametrize("duplicate", [False, True])
def test_env_r3_joker_destruction_removes_order_without_proceeds_and_updates_pool(duplicate):
    run = pristine_red_white_reset("DESTROY-JOKER")
    other_center = "j_joker" if duplicate else "j_jolly"
    for center, cost in (("j_joker", 2), (other_center, 2 if duplicate else 3)):
        joker = materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem(center, 1, cost, None, cost, center == "j_joker")
        )
        run.require_joker_order_state().acquire(joker, run.public.jokers)
        run.public.jokers.append(joker)
    run = suppress_visible_shop_jokers_from_generation_pool(run, run.public.jokers)
    before = run.rng_snapshot()
    # Destruction does not depend on observed resale value.
    run.public.jokers[0].sell_cost = None

    result = destroy_inventory_only_joker_exact(run, 0)

    assert result.public.money == run.public.money == 4
    assert [joker.center for joker in result.public.jokers] == [other_center]
    assert result.require_joker_order_state().creation_order == result.public.jokers
    keys = {record["key"] for record in result.public.joker_generation_pools["1"]}
    assert ("j_joker" in keys) is not duplicate
    assert result.rng_snapshot() == run.rng_snapshot() == before
    assert len(run.public.jokers) == 2


@pytest.mark.parametrize("boundary", ["resource", "eternal", "edition"])
def test_env_r3_joker_destruction_fails_closed_while_inverse_is_unowned(boundary):
    run = _shop_run(JugglerJoker() if boundary == "resource" else FlatMultJoker())
    joker = run.public.jokers[0]
    if boundary == "eternal":
        joker.eternal = True
    if boundary == "edition":
        joker.edition = "Negative"

    with pytest.raises(HeadlessTransitionError):
        destroy_inventory_only_joker_exact(run, 0)

    assert run.public.jokers == [joker]
    assert run.public.money == 7


def test_env_r3_exact_shop_joker_sale_credits_and_removes_inventory_only_joker():
    run = _shop_run()
    before_rng = run.rng_snapshot()

    assert can_sell_joker_exact(run, 0)
    result = sell_joker_exact(run, 0)

    assert result.public.money == 10
    assert result.public.jokers == []
    assert result.public.phase == "SHOP"
    assert result.public.shop_active is True
    assert result.rng_snapshot() == before_rng
    assert run.public.money == 7
    assert len(run.public.jokers) == 1
    assert run.rng_snapshot() == before_rng


@pytest.mark.parametrize("phase", ["BLIND_SELECT", "SELECTING_HAND", "BUFFOON_PACK"])
def test_env_r3_exact_sale_fails_closed_outside_active_main_shop(phase):
    run = _shop_run()
    run.public.phase = phase

    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="active SHOP"):
        sell_joker_exact(run, 0)

    run = _shop_run()
    run.public.shop_active = False
    assert not can_sell_joker_exact(run, 0)


def test_env_r3_exact_sale_fails_closed_for_unowned_inverse_and_metadata():
    run = _shop_run(TroubadourJoker())
    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="inverse lifecycle"):
        sell_joker_exact(run, 0)

    for field, value, message in (
        ("eternal", True, "Eternal"),
        ("edition", "NEGATIVE", "editions"),
        ("sell_cost", True, "sell_cost"),
        ("sell_cost", -1, "sell_cost"),
    ):
        run = _shop_run()
        setattr(run.public.jokers[0], field, value)
        assert not can_sell_joker_exact(run, 0)
        with pytest.raises(HeadlessTransitionError, match=message):
            sell_joker_exact(run, 0)


def test_env_r3_exact_sale_rejects_inexact_index_and_money():
    run = _shop_run()
    for index in (True, -1, 1):
        assert not can_sell_joker_exact(run, index)

    run.public.money = True
    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="integer money"):
        sell_joker_exact(run, 0)


def test_env_r3_exact_sale_rejects_non_run_input():
    assert not can_sell_joker_exact(object(), 0)
    with pytest.raises(TypeError, match="HeadlessRunState"):
        sell_joker_exact(object(), 0)


def test_env_r3_shop_backend_masks_and_executes_only_exact_joker_sales():
    first = FlatMultJoker()
    first.sell_cost = 2
    first.live_id = 10
    second = FlatMultJoker()
    second.sell_cost = 4
    second.live_id = 20
    run = _shop_run(first)
    run.public.jokers.append(second)
    run.joker_order_state = None
    run = HeadlessRunState(public=run.public, seed="SELL-MASK")
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert result.public.money == 10
    assert len(result.public.jokers) == 1
    assert result.public.jokers[0].live_id == 20
    result.require_joker_order_state()
    assert [joker.live_id for joker in result.joker_order_state.creation_order] == [20]
    assert [joker.live_id for joker in result.joker_order_state.physical_order] == [20]
    assert [joker.live_id for joker in run.public.jokers] == [10, 20]


def test_env_r3_shop_backend_masks_resource_sensitive_sale():
    run = _shop_run(TroubadourJoker())
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, action)


def test_env_r3_exact_juggler_sale_applies_hand_size_inverse_once():
    run = _shop_run(JugglerJoker())
    run.public.hand_size = 9
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert run.public.hand_size == 9
    assert len(run.public.jokers) == 1
    assert result.public.hand_size == 8
    assert result.public.jokers == []
    assert result.public.money == 10


@pytest.mark.parametrize("hand_size", [True, 0, -1])
def test_env_r3_juggler_sale_requires_exact_positive_hand_size(hand_size):
    run = _shop_run(JugglerJoker())
    run.public.hand_size = hand_size

    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="positive hand size"):
        sell_joker_exact(run, 0)


def test_env_r3_exact_drunkard_sale_applies_persistent_discard_inverse_once():
    run = _shop_run(DrunkardJoker())
    run.public.round_reset_discards_observed = True
    run.public.round_reset_discards = 4
    run.public.discards_remaining = 2
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert run.public.round_reset_discards == 4
    assert run.public.discards_remaining == 2
    assert result.public.round_reset_discards == 3
    assert result.public.discards_remaining == 2
    assert result.public.jokers == []
    assert result.public.money == 10


def test_env_r3_exact_golden_joker_sale_is_inventory_only():
    run = _shop_run(GoldenJoker())
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert run.public.jokers and type(run.public.jokers[0]) is GoldenJoker
    assert result.public.jokers == []
    assert result.public.money == 10


def test_env_r3_exact_bull_sale_is_inventory_only():
    run = _shop_run(BullJoker())
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert run.public.jokers and type(run.public.jokers[0]) is BullJoker
    assert result.public.jokers == []
    assert result.public.money == 10


def test_env_r3_exact_rocket_sale_is_inventory_only():
    run = _shop_run(RocketJoker())
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert run.public.jokers and type(run.public.jokers[0]) is RocketJoker
    assert result.public.jokers == []
    assert result.public.money == 10


def test_env_r3_exact_vampire_sale_is_inventory_only():
    vampire = VampireJoker()
    vampire.x_mult = 1.7
    run = _shop_run(vampire)
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert run.public.jokers and type(run.public.jokers[0]) is VampireJoker
    assert run.public.jokers[0].x_mult == 1.7
    assert result.public.jokers == []
    assert result.public.money == 10


@pytest.mark.parametrize(
    ("observed", "round_reset_discards", "message"),
    [
        (False, 4, "authoritative"),
        (True, True, "positive"),
        (True, 0, "positive"),
        (True, -1, "positive"),
    ],
)
def test_env_r3_drunkard_sale_requires_exact_persistent_discard_state(
    observed,
    round_reset_discards,
    message,
):
    run = _shop_run(DrunkardJoker())
    run.public.round_reset_discards_observed = observed
    run.public.round_reset_discards = round_reset_discards

    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match=message):
        sell_joker_exact(run, 0)
