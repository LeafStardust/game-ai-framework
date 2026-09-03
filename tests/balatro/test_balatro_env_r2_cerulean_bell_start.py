import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import (
    prepare_supported_cerulean_bell_start,
    start_supported_cerulean_bell,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.turtle_bean import TurtleBeanJoker
from games.balatro.state import BalatroState


def _run(seed: str = "TESTSEED") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.round = 2
    state.blind = Blind(BlindType.BOSS, requirement=100_000)
    state.boss_name = "Cerulean Bell"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed=seed)


def _identity(card):
    return card.rank, card.suit


def test_env_r2_cerulean_bell_prepare_owns_only_predeal_lifecycle():
    run = _run()

    result = prepare_supported_cerulean_bell_start(run)

    assert result.public.round == 3
    assert result.public.blind_score == 100_000
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.hand == []
    assert "nr1" not in result.rng.nodes
    assert "cerulean_bell" not in result.rng.nodes
    assert run.public.round == 2
    assert run.public.phase == "BLIND_SELECT"


def test_env_r2_cerulean_bell_full_start_composes_deal_then_forced_selection():
    result = start_supported_cerulean_bell(_run())

    assert result.public.round == 3
    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    forced = [card for card in result.public.hand if card.forced_selection]
    assert len(forced) == 1
    assert _identity(forced[0]) == ("4", "Clubs")
    assert "nr1" in result.rng.nodes
    assert "cerulean_bell" in result.rng.nodes


def test_env_r2_cerulean_bell_full_start_isolates_input_state_and_rng():
    run = _run()
    before_rng = run.rng_snapshot()

    result = start_supported_cerulean_bell(run)

    assert run.public.phase == "BLIND_SELECT"
    assert run.public.hand == []
    assert run.draw_pile == []
    assert run.rng_snapshot() == before_rng
    assert result.rng_snapshot() != before_rng


def test_env_r2_cerulean_bell_rejects_wrong_boss_name():
    run = _run()
    run.public.boss_name = "The Wall"

    with pytest.raises(HeadlessTransitionError, match="requires Cerulean Bell"):
        prepare_supported_cerulean_bell_start(run)


def test_env_r2_cerulean_bell_keeps_unclassified_setting_blind_jokers_fail_closed():
    run = _run()
    run.public.jokers = [TurtleBeanJoker()]

    with pytest.raises(HeadlessTransitionError, match="unsupported identity"):
        start_supported_cerulean_bell(run)


def test_env_r2_cerulean_bell_rejects_active_tags_and_vouchers():
    run = _run()
    run.tags = ["Double Tag"]
    with pytest.raises(HeadlessTransitionError, match="active tags"):
        prepare_supported_cerulean_bell_start(run)

    run = _run()
    run.public.vouchers = ["Grabber"]
    with pytest.raises(HeadlessTransitionError, match="vouchers"):
        prepare_supported_cerulean_bell_start(run)
