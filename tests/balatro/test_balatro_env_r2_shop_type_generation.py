import pytest

from games.balatro.env.shop_generation import (
    _shop_type_from_polled_rate,
    poll_base_shop_card_type,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(seed: str = "TESTSEED", *, ante: int = 1) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = ante
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_base_shop_type_weight_boundaries_match_vanilla_order():
    # Base normal rates are Joker 20, Tarot 4, Planet 4, Base 0, Spectral 0.
    assert _shop_type_from_polled_rate(0.5) == "Joker"
    assert _shop_type_from_polled_rate(20.0) == "Joker"
    assert _shop_type_from_polled_rate(20.000001) == "Tarot"
    assert _shop_type_from_polled_rate(24.0) == "Tarot"
    assert _shop_type_from_polled_rate(24.000001) == "Planet"
    assert _shop_type_from_polled_rate(27.999999) == "Planet"


def test_env_r2_base_shop_type_poll_uses_ante_key_and_isolates_input_rng():
    run = _run(ante=2)
    before = run.rng_snapshot()

    result = poll_base_shop_card_type(run)

    assert result.card_type in {"Joker", "Tarot", "Planet"}
    assert run.rng_snapshot() == before
    assert "cdt2" not in run.rng.nodes
    assert "cdt2" in result.run.rng.nodes
    assert "cdt1" not in result.run.rng.nodes


def test_env_r2_base_shop_type_poll_replays_exactly_from_same_seed_and_state():
    first = poll_base_shop_card_type(_run(seed="SHOPTYPE", ante=3))
    second = poll_base_shop_card_type(_run(seed="SHOPTYPE", ante=3))

    assert first.card_type == second.card_type
    assert first.run.rng_snapshot() == second.run.rng_snapshot()


def test_env_r2_base_shop_type_poll_advances_same_key_across_multiple_slots():
    first = poll_base_shop_card_type(_run(seed="SHOPTYPE", ante=1))
    # The primitive intentionally leaves inventory unmaterialized, so a caller
    # may perform the next source-order type poll on the returned RNG state.
    second = poll_base_shop_card_type(first.run)

    assert first.run.rng.nodes["cdt1"] != second.run.rng.nodes["cdt1"]


def test_env_r2_base_shop_type_poll_requires_exact_unmodified_shop_boundary():
    run = _run()
    run.public.phase = "BLIND_SELECT"
    with pytest.raises(HeadlessTransitionError, match="active SHOP"):
        poll_base_shop_card_type(run)

    run = _run()
    run.public.vouchers.append("v_tarot_merchant")
    with pytest.raises(HeadlessTransitionError, match="voucher-modified"):
        poll_base_shop_card_type(run)

    run = _run()
    run.tags.append("tag_coupon")
    with pytest.raises(HeadlessTransitionError, match="Tag"):
        poll_base_shop_card_type(run)

    run = _run()
    run.public.shop_jokers.append(object())
    with pytest.raises(HeadlessTransitionError, match="ungenerated inventory"):
        poll_base_shop_card_type(run)


def test_env_r2_base_shop_type_mapping_rejects_malformed_direct_rolls():
    with pytest.raises(TypeError, match="numeric"):
        _shop_type_from_polled_rate(True)
    with pytest.raises(ValueError, match="outside"):
        _shop_type_from_polled_rate(-0.1)
    with pytest.raises(ValueError, match="outside"):
        _shop_type_from_polled_rate(0.0)
    with pytest.raises(ValueError, match="outside"):
        _shop_type_from_polled_rate(28.1)
