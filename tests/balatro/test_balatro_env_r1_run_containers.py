import pytest

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.money = 0
    state.hand_size = 8
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.joker_slots = 5
    state.consumable_slots = 2
    return state


@pytest.mark.parametrize("seed", (True, 1.5, None, [], {}))
def test_balatro_env_r1_seed_requires_string_or_exact_integer(seed):
    with pytest.raises(
        HeadlessTransitionError,
        match="seed must be a string or exact integer",
    ):
        HeadlessRunState(public=_state(), seed=seed)


@pytest.mark.parametrize("seed", (0, -7, 42, "seed", ""))
def test_balatro_env_r1_seed_accepts_declared_deterministic_types(seed):
    run = HeadlessRunState(public=_state(), seed=seed)
    assert run.seed == seed


def test_balatro_env_r1_tags_require_string_list():
    with pytest.raises(HeadlessTransitionError, match="tags must be a list"):
        HeadlessRunState(public=_state(), seed=46, tags=("tag_double",))

    with pytest.raises(
        HeadlessTransitionError,
        match="tags must contain only strings",
    ):
        HeadlessRunState(public=_state(), seed=46, tags=["tag_double", 3])

    run = HeadlessRunState(
        public=_state(),
        seed=46,
        tags=["tag_double", "tag_skip"],
    )
    assert run.tags == ["tag_double", "tag_skip"]


def test_balatro_env_r1_pack_choices_require_list_without_inventing_r2_item_schema():
    with pytest.raises(HeadlessTransitionError, match="pack_choices must be a list"):
        HeadlessRunState(public=_state(), seed=47, pack_choices=("choice",))

    marker = object()
    run = HeadlessRunState(public=_state(), seed=47, pack_choices=[marker])
    assert run.pack_choices == [marker]
