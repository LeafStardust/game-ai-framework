from __future__ import annotations

import copy
from types import SimpleNamespace

from games.balatro.joker import Joker
from games.balatro.live.riff_raff_cycle import RiffRaffCyclePolicy


class StubJoker(Joker):
    def __init__(self, label: str, *, area_index: int, value: float) -> None:
        self.label = label
        self.area_index = area_index
        self.test_value = value
        self.sell_value = 1

    def apply(self, context):
        return context


class StubState:
    def __init__(self, jokers, *, joker_slots: int = 5, phase: str = "BLIND_SELECT") -> None:
        self.jokers = list(jokers)
        self.joker_slots = joker_slots
        self.phase = phase

    def copy(self):
        return copy.deepcopy(self)


class StubEvaluator:
    def evaluate(self, state, joker):
        del state
        return SimpleNamespace(total_gain=float(joker.test_value))


def _policy() -> RiffRaffCyclePolicy:
    return RiffRaffCyclePolicy(evaluator=StubEvaluator())


def test_riff_raff_cycles_two_low_value_jokers_then_stops():
    riff = StubJoker("Riff-Raff", area_index=0, value=99.0)
    junk_a = StubJoker("Junk A", area_index=1, value=0.1)
    junk_b = StubJoker("Junk B", area_index=2, value=0.2)
    useful_a = StubJoker("Useful A", area_index=3, value=4.0)
    useful_b = StubJoker("Useful B", area_index=4, value=5.0)
    state = StubState([riff, junk_a, junk_b, useful_a, useful_b])

    first = _policy().recommend(state, will_select_blind=True)
    assert first is not None
    assert first.joker == "Junk A"
    assert first.free_slots_before == 0

    state.jokers.pop(1)
    second = _policy().recommend(state, will_select_blind=True)
    assert second is not None
    assert second.joker == "Junk B"
    assert second.free_slots_before == 1

    state.jokers.pop(1)
    assert _policy().recommend(state, will_select_blind=True) is None


def test_riff_raff_never_sells_itself_or_helpful_jokers():
    riff = StubJoker("Riff-Raff", area_index=0, value=-5.0)
    useful = [
        StubJoker(f"Useful {index}", area_index=index, value=3.0)
        for index in range(1, 5)
    ]
    state = StubState([riff, *useful])

    assert _policy().recommend(state, will_select_blind=True) is None


def test_riff_raff_cycle_only_runs_before_actual_blind_selection():
    riff = StubJoker("Riff-Raff", area_index=0, value=99.0)
    junk = StubJoker("Junk", area_index=1, value=0.0)
    state = StubState([riff, junk], joker_slots=2)

    assert _policy().recommend(state, will_select_blind=False) is None

    state.phase = "SHOP"
    assert _policy().recommend(state, will_select_blind=True) is None
