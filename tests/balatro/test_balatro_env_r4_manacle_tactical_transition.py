import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_resource_boss
from games.balatro.env.boss_defeat import defeat_supported_boss
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.tactical_transition import apply_supported_tactical_discard
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _manacle_run(*, requirement=99_999, seed="R4-MANACLE"):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 1
    state.round = 3
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=5)
    state.boss_name = "The Manacle"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_resource_boss(HeadlessRunState(public=state, seed=seed))


def test_env_r4_manacle_play_refills_to_reduced_hand_size():
    run = _manacle_run()

    result = apply_supported_ordinary_play(run, (0,))

    assert len(run.public.hand) == run.public.hand_size == 7
    assert run.boss_hand_size_sub == 1
    assert len(result.public.hand) == result.public.hand_size == 7
    assert result.boss_hand_size_sub == 1
    assert result.public.hands_remaining == 3


def test_env_r4_manacle_discard_refills_to_reduced_hand_size():
    run = _manacle_run(seed="R4-MANACLE-DISCARD")

    result = apply_supported_tactical_discard(run, (0, 2))

    assert len(run.public.hand) == run.public.hand_size == 7
    assert len(result.public.hand) == result.public.hand_size == 7
    assert result.public.discards_remaining == 2
    assert result.public.discards_used == 1
    assert result.boss_hand_size_sub == 1


def test_env_r4_manacle_clear_restores_hand_size_only_at_defeat():
    run = _manacle_run(requirement=1, seed="R4-MANACLE-CLEAR")

    cleared = apply_supported_ordinary_play(run, (0,))
    defeated = defeat_supported_boss(cleared)

    assert cleared.public.phase == "ROUND_EVAL"
    assert cleared.public.hand_size == 7
    assert cleared.boss_hand_size_sub == 1
    assert defeated.public.hand_size == 8
    assert defeated.boss_hand_size_sub is None
    assert len(defeated.public.hand) == 6


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("boss_hand_size_sub", None),
        ("boss_hand_size_sub", 2),
        ("boss_hands_sub", 1),
        ("boss_discards_sub", 1),
    ],
)
def test_env_r4_manacle_rejects_inexact_private_resource_state_atomically(
    field,
    value,
):
    run = _manacle_run(seed=f"R4-MANACLE-BAD-{field}-{value}")
    setattr(run, field, value)
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="Manacle action"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before


def test_env_r4_manacle_rejects_wrong_hand_size_and_disabled_blind():
    wrong_size = _manacle_run(seed="R4-MANACLE-WRONG-SIZE")
    wrong_size.public.hand_size = 8
    with pytest.raises(HeadlessTransitionError, match="stored hand-size"):
        apply_supported_tactical_discard(wrong_size, (0,))

    disabled = _manacle_run(seed="R4-MANACLE-DISABLED")
    disabled.public.blind.disabled = True
    with pytest.raises(HeadlessTransitionError, match="active Boss"):
        apply_supported_ordinary_play(disabled, (0,))
