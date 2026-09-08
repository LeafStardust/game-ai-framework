import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import prepare_supported_nonboss_blind_start
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(*, vouchers=(), observed=True, reset_hands=4, reset_discards=3):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.blind = Blind(BlindType.SMALL, requirement=300)
    state.round_reset_hands_observed = True
    state.round_reset_hands = reset_hands
    state.round_reset_discards_observed = True
    state.round_reset_discards = reset_discards
    state.vouchers = list(vouchers)
    state.vouchers_observed = observed
    return HeadlessRunState(public=state, seed="VOUCHER-BLIND-START")


def test_env_r2_supported_shop_voucher_crosses_blind_start_without_reapplication():
    run = _run(vouchers=["v_hone"])

    result = prepare_supported_nonboss_blind_start(run)

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.vouchers == ["v_hone"]
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.vouchers == ["v_hone"]


def test_env_r2_resource_voucher_uses_already_persisted_round_allowance():
    run = _run(vouchers=["v_grabber"], reset_hands=5)

    result = prepare_supported_nonboss_blind_start(run)

    assert result.public.vouchers == ["v_grabber"]
    assert result.public.round_reset_hands == 5
    assert result.public.hands_remaining == 5


def test_env_r2_ante_voucher_history_crosses_blind_start_unchanged():
    run = _run(vouchers=["v_hieroglyph", "v_petroglyph"])

    result = prepare_supported_nonboss_blind_start(run)

    assert result.public.vouchers == ["v_hieroglyph", "v_petroglyph"]


@pytest.mark.parametrize(
    "vouchers, observed",
    [
        (["v_unknown"], True),
        (["v_grabber"], False),
        (["v_petroglyph"], True),
    ],
)
def test_env_r2_blind_start_rejects_inexact_voucher_ownership(vouchers, observed):
    run = _run(vouchers=vouchers, observed=observed)

    with pytest.raises(HeadlessTransitionError, match="exact supported vouchers"):
        prepare_supported_nonboss_blind_start(run)
