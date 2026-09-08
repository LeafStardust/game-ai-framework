import pytest

from games.balatro.env.boss_hand import apply_arm_debuff_hand_level
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.hand import PokerHand
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _run(*, level: int = 3) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SELECTING_HAND"
    state.boss_name = "The Arm"
    state.hand_levels["PAIR"] = level
    return HeadlessRunState(public=state, seed="TESTSEED")


def test_env_r2_arm_decrements_matching_hand_level_before_scoring():
    run = _run(level=3)

    result = apply_arm_debuff_hand_level(run, "PAIR")

    assert result.public.hand_levels["PAIR"] == 2
    assert run.public.hand_levels["PAIR"] == 3

    expected = BalatroState()
    expected.hand_levels["PAIR"] = 2
    assert BalatroScorer().score(PokerHand.PAIR, result.public) == BalatroScorer().score(
        PokerHand.PAIR,
        expected,
    )


def test_env_r2_arm_never_reduces_level_below_one():
    result = apply_arm_debuff_hand_level(_run(level=1), "PAIR")

    assert result.public.hand_levels["PAIR"] == 1


def test_env_r2_arm_only_mutates_the_classified_hand():
    run = _run(level=4)
    before = dict(run.public.hand_levels)

    result = apply_arm_debuff_hand_level(run, "PAIR")

    for hand_name, level in before.items():
        if hand_name == "PAIR":
            assert result.public.hand_levels[hand_name] == level - 1
        else:
            assert result.public.hand_levels[hand_name] == level


def test_env_r2_arm_rejects_invalid_level_state():
    for invalid_level in (True, 0, -1, 2.5, "2"):
        run = _run(level=1)
        run.public.hand_levels["PAIR"] = invalid_level
        with pytest.raises(HeadlessTransitionError, match="positive hand level"):
            apply_arm_debuff_hand_level(run, "PAIR")


def test_env_r2_arm_requires_canonical_hand_phase_and_identity():
    run = _run()
    with pytest.raises(HeadlessTransitionError, match="canonical classified"):
        apply_arm_debuff_hand_level(run, "Pair")

    run = _run()
    run.public.phase = "SHOP"
    with pytest.raises(HeadlessTransitionError, match="SELECTING_HAND"):
        apply_arm_debuff_hand_level(run, "PAIR")

    run = _run()
    run.public.boss_name = "The Ox"
    with pytest.raises(HeadlessTransitionError, match="requires The Arm"):
        apply_arm_debuff_hand_level(run, "PAIR")
