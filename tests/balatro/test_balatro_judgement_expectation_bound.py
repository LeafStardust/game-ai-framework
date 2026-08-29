from __future__ import annotations

from types import SimpleNamespace

from games.balatro.build.judgement_expectation import (
    _MAX_EVALUATED_RECORDS_PER_RARITY,
    _bounded_indices,
    JudgementExpectationEvaluator,
)


class _Factory:
    def create(self, record):
        return SimpleNamespace(
            name=str(record.get("label") or record.get("center") or "Joker"),
            edition=None,
        )


class _Value:
    def __init__(self):
        self.calls = 0

    def evaluate(self, state, candidate):
        del state, candidate
        self.calls += 1
        return SimpleNamespace(total_gain=1.0)


def _record(index: int, rarity: str):
    return {
        "center": f"j_{rarity.lower()}_{index}",
        "label": f"{rarity.title()} {index}",
        "ability_name": f"{rarity.title()} {index}",
        "ability_set": "JOKER",
        "rarity": rarity,
    }


def test_bounded_indices_spreads_across_full_pool_deterministically():
    indices = _bounded_indices(20, 6)

    assert len(indices) == 6
    assert indices[0] == 0
    assert indices[-1] == 19
    assert indices == _bounded_indices(20, 6)


def test_judgement_large_catalogue_uses_bounded_full_pool_lower_bound():
    value = _Value()
    evaluator = JudgementExpectationEvaluator(
        joker_factory=_Factory(),
        joker_value=value,
    )
    pools = {
        rarity: tuple(_record(index, rarity) for index in range(30))
        for rarity in ("COMMON", "UNCOMMON", "RARE")
    }
    state = SimpleNamespace(
        joker_slots=5,
        jokers=(),
        stake_name="WHITE",
        joker_generation_pool_observed=True,
        joker_generation_pools=pools,
        visible_poker_hands=("HIGH_CARD", "PAIR"),
        joker_generation_edition_rate=1.0,
    )

    result = evaluator.evaluate(state)

    assert result.available is True
    assert result.complete is True
    assert result.outcome_count == 3 * _MAX_EVALUATED_RECORDS_PER_RARITY
    assert 0.0 < result.expected_total_gain < 1.0
    assert value.calls <= 3 * _MAX_EVALUATED_RECORDS_PER_RARITY * 4
    assert any("evaluated=6/30" in note for note in result.rationale)
    assert any("omitted probability mass remains zero" in note for note in result.rationale)
