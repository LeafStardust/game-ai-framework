import pytest

from games.balatro.env.voucher_capabilities import (
    SHOP_BASE_GENERATION_VOUCHER_KEYS,
    blind_start_vouchers_are_exact,
)
from games.balatro.state import BalatroState


def _state(vouchers=(), *, observed=True):
    state = BalatroState()
    state.vouchers = list(vouchers)
    state.vouchers_observed = observed
    return state


def test_env_r2_blind_start_accepts_each_supported_voucher_identity():
    for voucher in SHOP_BASE_GENERATION_VOUCHER_KEYS:
        if voucher == "v_petroglyph":
            state = _state(["v_hieroglyph", "v_petroglyph"])
        else:
            state = _state([voucher])
        assert blind_start_vouchers_are_exact(state), voucher


def test_env_r2_blind_start_accepts_empty_voucher_ownership_without_observation():
    assert blind_start_vouchers_are_exact(_state([], observed=False))


def test_env_r2_blind_start_rejects_nonempty_unobserved_voucher_ownership():
    assert not blind_start_vouchers_are_exact(_state(["v_grabber"], observed=False))


def test_env_r2_blind_start_rejects_duplicate_voucher_ownership():
    assert not blind_start_vouchers_are_exact(
        _state(["v_grabber", "v_grabber"])
    )


def test_env_r2_blind_start_rejects_unsupported_or_malformed_vouchers():
    assert not blind_start_vouchers_are_exact(_state(["v_unknown"]))
    assert not blind_start_vouchers_are_exact(_state([""]))

    state = _state()
    state.vouchers = [123]
    assert not blind_start_vouchers_are_exact(state)


def test_env_r2_blind_start_requires_hieroglyph_before_petroglyph():
    assert not blind_start_vouchers_are_exact(_state(["v_petroglyph"]))
    assert blind_start_vouchers_are_exact(
        _state(["v_hieroglyph", "v_petroglyph"])
    )


def test_env_r2_blind_start_voucher_boundary_rejects_non_state_input():
    with pytest.raises(TypeError, match="BalatroState"):
        blind_start_vouchers_are_exact(object())
