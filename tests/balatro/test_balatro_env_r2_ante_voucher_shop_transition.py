import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.env.voucher_capabilities import shop_generation_vouchers_are_exact
from games.balatro.state import BalatroState


def _run(
    key: str,
    *,
    owned: list[str] | None = None,
    progression: BlindProgressionState | None = None,
    include_progression: bool = True,
) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 30
    state.ante = 4
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.hands_remaining = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 4
    state.discards_remaining = 4
    state.vouchers = list(owned or [])
    state.vouchers_observed = bool(state.vouchers)
    state.shop_vouchers = [
        GeneratedShopVoucherItem(center_key=key, base_cost=10, price=10)
    ]
    return HeadlessRunState(
        public=state,
        seed="ANTE-SHOP",
        blind_progression_state=(
            progression
            if progression is not None
            else (BlindProgressionState(blind_ante=4) if include_progression else None)
        ),
    )


def _buy_action() -> EnvAction:
    return EnvAction.from_alias("BUY_VOUCHER", {"slot": 0})


def test_env_r2_hieroglyph_is_training_legal_through_canonical_shop_engine():
    run = _run("v_hieroglyph")

    assert _buy_action() in ShopTransitionEngine().legal_actions(run)


def test_env_r2_hieroglyph_shop_step_is_atomic_and_isolates_input():
    run = _run("v_hieroglyph")
    before_rng = run.rng_snapshot()

    result = ShopTransitionEngine().step(run, _buy_action())

    assert run.public.money == 30
    assert run.public.ante == 4
    assert run.public.vouchers == []
    assert len(run.public.shop_vouchers) == 1
    assert run.require_blind_progression_state().blind_ante == 4
    assert run.public.round_reset_hands == 4
    assert run.public.hands_remaining == 4

    assert result.public.money == 20
    assert result.public.ante == 3
    assert result.public.vouchers == ["v_hieroglyph"]
    assert result.public.vouchers_observed is True
    assert result.public.shop_vouchers == []
    assert result.require_blind_progression_state().blind_ante == 3
    assert result.public.round_reset_hands == 3
    assert result.public.hands_remaining == 3
    assert result.public.round_reset_discards == 4
    assert result.public.discards_remaining == 4
    assert result.rng_snapshot() == before_rng


def test_env_r2_petroglyph_requires_hieroglyph_in_shop_mask():
    engine = ShopTransitionEngine()
    run = _run("v_petroglyph")

    assert _buy_action() not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, _buy_action())


def test_env_r2_petroglyph_shop_step_preserves_voucher_redemption_order():
    run = _run("v_petroglyph", owned=["v_hieroglyph"])
    engine = ShopTransitionEngine()

    assert _buy_action() in engine.legal_actions(run)
    result = engine.step(run, _buy_action())

    assert result.public.money == 20
    assert result.public.ante == 3
    assert result.require_blind_progression_state().blind_ante == 3
    assert result.public.vouchers == ["v_hieroglyph", "v_petroglyph"]
    assert result.public.round_reset_discards == 3
    assert result.public.discards_remaining == 3
    assert result.public.round_reset_hands == 4
    assert result.public.hands_remaining == 4


def test_env_r2_ante_voucher_mask_fails_closed_without_or_with_stale_progression():
    engine = ShopTransitionEngine()

    missing = _run("v_hieroglyph", include_progression=False)
    assert _buy_action() not in engine.legal_actions(missing)

    stale = _run(
        "v_hieroglyph",
        progression=BlindProgressionState(blind_ante=3),
    )
    assert _buy_action() not in engine.legal_actions(stale)


def test_env_r2_ante_voucher_mask_requires_observed_reducible_allowances():
    engine = ShopTransitionEngine()

    hierarchy = _run("v_hieroglyph")
    hierarchy.public.round_reset_hands_observed = False
    assert _buy_action() not in engine.legal_actions(hierarchy)

    hierarchy = _run("v_hieroglyph")
    hierarchy.public.round_reset_hands = 0
    assert _buy_action() not in engine.legal_actions(hierarchy)

    petroglyph = _run("v_petroglyph", owned=["v_hieroglyph"])
    petroglyph.public.round_reset_discards_observed = False
    assert _buy_action() not in engine.legal_actions(petroglyph)

    petroglyph = _run("v_petroglyph", owned=["v_hieroglyph"])
    petroglyph.public.round_reset_discards = 0
    assert _buy_action() not in engine.legal_actions(petroglyph)


def test_env_r2_valid_ante_voucher_history_is_neutral_for_shop_generation_capability():
    state = BalatroState()
    state.vouchers = ["v_hieroglyph"]
    state.vouchers_observed = True
    assert shop_generation_vouchers_are_exact(state)

    state.vouchers = ["v_hieroglyph", "v_petroglyph"]
    assert shop_generation_vouchers_are_exact(state)


def test_env_r2_petroglyph_without_hieroglyph_poison_shop_generation_capability():
    state = BalatroState()
    state.vouchers = ["v_petroglyph"]
    state.vouchers_observed = True

    assert not shop_generation_vouchers_are_exact(state)
