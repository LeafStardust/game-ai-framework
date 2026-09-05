import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.skip_blind import can_skip_blind_exact, skip_blind_exact
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(*, money: int = 17, tag: str = "tag_economy") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 2
    state.money = money
    state.blind = Blind(
        BlindType.SMALL,
        requirement=800,
        reward=3,
        tag_key=tag,
    )
    progression = BlindProgressionState(
        small_status="Select",
        big_status="Upcoming",
        boss_status="Upcoming",
        blind_on_deck="Small",
        blind_ante=2,
        boss_name="The House",
        small_tag=tag,
        big_tag="tag_meteor",
    )
    return HeadlessRunState(
        public=state,
        seed="SKIP-BLIND",
        blind_progression_state=progression,
    )


@pytest.mark.parametrize(
    ("money", "expected"),
    [(17, 34), (50, 90), (-4, -4)],
)
def test_env_r3_small_economy_skip_applies_exact_transition(money, expected):
    run = _run(money=money)

    result = skip_blind_exact(run)

    assert result.public.money == expected
    assert result.skips == 1
    assert result.public.phase == "BLIND_SELECT"
    assert result.public.blind.type is BlindType.BIG
    assert result.public.blind.requirement == 1_200
    assert result.public.blind.reward == 4
    assert result.public.blind.tag_key == "tag_meteor"
    progression = result.require_blind_progression_state()
    assert progression.small_status == "Skipped"
    assert progression.big_status == "Select"
    assert progression.blind_on_deck == "Big"
    assert result.tags == []


def test_env_r3_small_economy_skip_isolates_input_and_consumes_no_rng():
    run = _run()
    before_rng = run.rng_snapshot()

    assert can_skip_blind_exact(run)
    result = skip_blind_exact(run)

    assert run.public.money == 17
    assert run.skips == 0
    assert run.public.blind.type is BlindType.SMALL
    assert run.require_blind_progression_state().small_status == "Select"
    assert result.rng_snapshot() == before_rng
    assert run.rng_snapshot() == before_rng


@pytest.mark.parametrize("tag", ["tag_buffoon", "tag_double", "tag_juggle"])
def test_env_r3_skip_blind_fails_closed_for_unowned_tag_outcomes(tag):
    run = _run(tag=tag)

    assert not can_skip_blind_exact(run)
    with pytest.raises(HeadlessTransitionError, match="Tag outcome is not exact"):
        skip_blind_exact(run)


def test_env_r3_skip_blind_fails_closed_for_big_boss_and_inconsistent_state():
    run = _run()
    run.public.blind = Blind(
        BlindType.BIG,
        requirement=1_200,
        reward=4,
        tag_key="tag_economy",
    )
    assert not can_skip_blind_exact(run)

    run = _run()
    run.require_blind_progression_state().small_tag = "tag_buffoon"
    assert not can_skip_blind_exact(run)

    run = _run()
    run.tags.append("tag_double")
    assert not can_skip_blind_exact(run)


def test_env_r3_skip_blind_rejects_non_run_input():
    with pytest.raises(TypeError, match="HeadlessRunState"):
        can_skip_blind_exact(object())
    with pytest.raises(TypeError, match="HeadlessRunState"):
        skip_blind_exact(object())
