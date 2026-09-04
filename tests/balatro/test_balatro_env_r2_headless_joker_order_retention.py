from games.balatro.env.actions import EnvAction
from games.balatro.env.transition import HeadlessRunState, ShopTransitionEngine
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.state import BalatroState


def _shop_run(*items) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 20
    state.joker_slots = 5
    for item in items:
        item.cost = 1
    state.shop_jokers = list(items)
    return HeadlessRunState(public=state, seed="AMBER-ORDER")


def test_env_r2_empty_headless_run_starts_with_exact_empty_joker_order():
    run = _shop_run()

    order = run.require_joker_order_state()

    assert order.creation_order == []
    assert order.physical_order == []


def test_env_r2_shop_purchases_retain_creation_order_without_synthetic_live_ids():
    first = FlatMultJoker()
    second = JollyJoker()
    run = _shop_run(first, second)
    engine = ShopTransitionEngine()

    after_first = engine.step(run, EnvAction.from_alias("BUY_JOKER", {"slot": 0}))
    after_second = engine.step(
        after_first,
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
    )

    order = after_second.require_joker_order_state()
    assert order.creation_order == after_second.public.jokers
    assert order.physical_order == after_second.public.jokers
    assert [type(joker) for joker in order.creation_order] == [FlatMultJoker, JollyJoker]
    assert all(getattr(joker, "live_id", None) is None for joker in after_second.public.jokers)


def test_env_r2_purchase_order_state_is_isolated_from_input_snapshot():
    joker = FlatMultJoker()
    run = _shop_run(joker)
    before = run.require_joker_order_state()

    result = ShopTransitionEngine().step(
        run,
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
    )

    assert before.creation_order == []
    assert before.physical_order == []
    assert run.public.jokers == []
    assert len(result.require_joker_order_state().creation_order) == 1


def test_env_r2_deepcopy_retained_order_points_to_copied_public_jokers():
    first = FlatMultJoker()
    second = JollyJoker()
    run = _shop_run(first, second)
    engine = ShopTransitionEngine()
    run = engine.step(run, EnvAction.from_alias("BUY_JOKER", {"slot": 0}))
    run = engine.step(run, EnvAction.from_alias("BUY_JOKER", {"slot": 0}))

    copied = run.copy()
    copied_order = copied.require_joker_order_state()

    assert copied.public.jokers is not run.public.jokers
    assert {id(joker) for joker in copied_order.creation_order} == {
        id(joker) for joker in copied.public.jokers
    }
    assert {id(joker) for joker in copied_order.creation_order}.isdisjoint(
        {id(joker) for joker in run.public.jokers}
    )
