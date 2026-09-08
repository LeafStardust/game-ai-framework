from types import SimpleNamespace

from games.balatro.joker import JokerContext
from games.balatro.jokers.dagger import DaggerJoker
from games.balatro.state import BalatroState


def _state_with_target(*, eternal: bool, sell_value: int = 5):
    state = BalatroState()
    dagger = DaggerJoker()
    target = SimpleNamespace(eternal=eternal, sell_value=sell_value)
    state.jokers = [dagger, target]
    return state, dagger, target


def test_dagger_does_not_destroy_or_scale_from_eternal_target() -> None:
    state, dagger, target = _state_with_target(eternal=True, sell_value=7)
    context = JokerContext(state=state, trigger="BLIND_SELECTED")

    result = dagger.apply(context)

    assert dagger.mult == 0
    assert "destroy_joker" not in result.data
    assert state.jokers == [dagger, target]


def test_dagger_scales_from_and_requests_destruction_of_normal_target() -> None:
    state, dagger, target = _state_with_target(eternal=False, sell_value=7)
    context = JokerContext(state=state, trigger="BLIND_SELECTED")

    result = dagger.apply(context)

    assert dagger.mult == 14
    assert result.data["destroy_joker"] is target
