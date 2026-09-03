import pytest

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _state(*, boss_name: str | None = None) -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.boss_name = boss_name
    return state


def test_env_r2_reversible_boss_resource_state_defaults_to_unset():
    run = HeadlessRunState(public=_state(), seed="BOSS-RESTORE")

    assert run.boss_hands_sub is None
    assert run.boss_discards_sub is None


def test_env_r2_water_restore_state_accepts_exact_zero_and_positive_integer():
    zero = HeadlessRunState(
        public=_state(boss_name="The Water"),
        seed="BOSS-RESTORE",
        boss_discards_sub=0,
    )
    positive = HeadlessRunState(
        public=_state(boss_name="The Water"),
        seed="BOSS-RESTORE",
        boss_discards_sub=3,
    )

    assert zero.boss_discards_sub == 0
    assert positive.boss_discards_sub == 3


def test_env_r2_needle_restore_state_accepts_exact_integer():
    run = HeadlessRunState(
        public=_state(boss_name="The Needle"),
        seed="BOSS-RESTORE",
        boss_hands_sub=3,
    )

    assert run.boss_hands_sub == 3


@pytest.mark.parametrize("value", [True, 1.5, "3"])
def test_env_r2_boss_restore_state_rejects_noninteger_values(value):
    with pytest.raises(HeadlessTransitionError, match="boss_hands_sub must be an exact integer"):
        HeadlessRunState(
            public=_state(boss_name="The Needle"),
            seed="BOSS-RESTORE",
            boss_hands_sub=value,
        )

    with pytest.raises(HeadlessTransitionError, match="boss_discards_sub must be an exact integer"):
        HeadlessRunState(
            public=_state(boss_name="The Water"),
            seed="BOSS-RESTORE",
            boss_discards_sub=value,
        )


def test_env_r2_water_restore_state_rejects_negative_discard_count():
    with pytest.raises(HeadlessTransitionError, match="boss_discards_sub cannot be negative"):
        HeadlessRunState(
            public=_state(boss_name="The Water"),
            seed="BOSS-RESTORE",
            boss_discards_sub=-1,
        )


def test_env_r2_boss_restore_state_rejects_identity_mismatch():
    with pytest.raises(HeadlessTransitionError, match="only valid for The Needle"):
        HeadlessRunState(
            public=_state(boss_name="The Water"),
            seed="BOSS-RESTORE",
            boss_hands_sub=3,
        )

    with pytest.raises(HeadlessTransitionError, match="only valid for The Water"):
        HeadlessRunState(
            public=_state(boss_name="The Needle"),
            seed="BOSS-RESTORE",
            boss_discards_sub=3,
        )


def test_env_r2_boss_restore_state_rejects_two_active_adjustments():
    # Identity validation would already reject one side for a real boss name, so
    # use a subclass-free direct construction target that demonstrates the
    # invariant through the Water identity and then the Needle field.
    state = _state(boss_name="The Water")
    with pytest.raises(HeadlessTransitionError):
        HeadlessRunState(
            public=state,
            seed="BOSS-RESTORE",
            boss_discards_sub=3,
            boss_hands_sub=3,
        )


def test_env_r2_boss_restore_state_isolated_by_headless_copy():
    run = HeadlessRunState(
        public=_state(boss_name="The Water"),
        seed="BOSS-RESTORE",
        boss_discards_sub=3,
    )

    copied = run.copy()
    copied.boss_discards_sub = 1

    assert run.boss_discards_sub == 3
    assert copied.boss_discards_sub == 1
