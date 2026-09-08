from games.balatro.arcana_booster_expectation_policy import (
    _MAX_EVALUATED_RECORDS_LARGE_POOL,
    ArcanaBoosterExpectationEvaluator,
)
from games.balatro.state import BalatroState


def _state_with_pool(count: int) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.consumable_generation_pool_observed = True
    state.consumable_generation_pools = {
        "TAROT": [
            {
                "center": f"c_test_{index}",
                "label": f"Test Tarot {index}",
                "ability_name": f"Test Tarot {index}",
                "ability_set": "TAROT",
            }
            for index in range(count)
        ]
    }
    state.soul_generation_available = False
    return state


def test_large_arcana_pool_uses_bounded_spread_and_full_denominator(monkeypatch):
    state = _state_with_pool(22)
    evaluator = ArcanaBoosterExpectationEvaluator()
    seen: list[int] = []

    def visible_value(_state, record):
        seen.append(int(str(record["center"]).rsplit("_", 1)[-1]))
        return 1.0

    monkeypatch.setattr(evaluator, "_visible_value", visible_value)

    expected, positive, evaluated, total = evaluator._ordinary_pool_mean(state, "TAROT")

    assert total == 22
    assert evaluated == _MAX_EVALUATED_RECORDS_LARGE_POOL
    assert len(seen) == _MAX_EVALUATED_RECORDS_LARGE_POOL
    assert seen[0] == 0
    assert seen[-1] == 21
    assert expected == _MAX_EVALUATED_RECORDS_LARGE_POOL / 22.0
    assert positive == _MAX_EVALUATED_RECORDS_LARGE_POOL / 22.0


def test_small_arcana_pool_remains_exact(monkeypatch):
    state = _state_with_pool(12)
    evaluator = ArcanaBoosterExpectationEvaluator()
    calls = 0

    def visible_value(_state, _record):
        nonlocal calls
        calls += 1
        return 2.0

    monkeypatch.setattr(evaluator, "_visible_value", visible_value)

    expected, positive, evaluated, total = evaluator._ordinary_pool_mean(state, "TAROT")

    assert total == 12
    assert evaluated == 12
    assert calls == 12
    assert expected == 2.0
    assert positive == 1.0
