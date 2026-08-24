from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

import games.balatro
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.forming_strategy_retention_policy import apply_forming_strategy_retention
from games.balatro.joker_policy import HOLD, REPLACE
from games.balatro.pinned_strategy_retention_policy import apply_pinned_strategy_retention


class BurntJoker:
    area_index = 0


class RandomJoker:
    area_index = 0


@dataclass(frozen=True)
class _Selected:
    replace_index: int = 0


@dataclass(frozen=True)
class _Decision:
    action: str = REPLACE
    selected: _Selected | None = _Selected()
    rationale: tuple[str, ...] = ()


def _composition(*, plan=None, pinned=None, candidates=()):
    return SimpleNamespace(
        strategy_plan=plan,
        pinned_strategy_id=pinned,
        strategy_candidates=tuple(candidates),
    )


def _plan(strategy_id="burnt_target_level", commitment=StrategyCommitment.FORMING, strength=5.0):
    return SimpleNamespace(
        strategy_id=strategy_id,
        commitment=commitment,
        strength=strength,
    )


def _candidate(strategy_id, commitment, strength):
    return SimpleNamespace(
        strategy_id=strategy_id,
        commitment=commitment,
        strength=strength,
    )


def test_forming_known_strategy_is_not_protected_by_pinned_retention():
    state = SimpleNamespace(jokers=[BurntJoker()], joker_slots=1)
    decision = _Decision()
    with patch(
        "games.balatro.pinned_strategy_retention_policy.evaluate_bond_composition",
        return_value=((), _composition(plan=_plan())),
    ):
        result = apply_pinned_strategy_retention(state, RandomJoker(), decision)
    assert result.action == REPLACE


def test_forming_retention_vetoes_replacement_that_erases_known_plan():
    state = SimpleNamespace(jokers=[BurntJoker()], joker_slots=1)
    current = _composition(
        plan=_plan(),
        candidates=(_candidate("burnt_target_level", StrategyCommitment.FORMING, 5.0),),
    )
    projected = _composition(plan=None, pinned=None, candidates=())
    with patch(
        "games.balatro.forming_strategy_retention_policy.evaluate_bond_composition",
        side_effect=[((), current), ((), projected)],
    ), patch(
        "games.balatro.forming_strategy_retention_policy.projected_state_with_jokers",
        return_value=object(),
    ):
        result = apply_forming_strategy_retention(state, RandomJoker(), _Decision())

    assert result.action == HOLD
    assert result.selected is None
    assert any("forming strategy retention veto" in note for note in result.rationale)


def test_forming_retention_allows_replacement_that_preserves_same_plan():
    state = SimpleNamespace(jokers=[BurntJoker()], joker_slots=1)
    current = _composition(plan=_plan())
    projected = _composition(plan=_plan(strength=6.0))
    with patch(
        "games.balatro.forming_strategy_retention_policy.evaluate_bond_composition",
        side_effect=[((), current), ((), projected)],
    ), patch(
        "games.balatro.forming_strategy_retention_policy.projected_state_with_jokers",
        return_value=object(),
    ):
        result = apply_forming_strategy_retention(state, RandomJoker(), _Decision())

    assert result.action == REPLACE


def test_forming_retention_allows_materially_stronger_pinned_escape():
    state = SimpleNamespace(jokers=[BurntJoker()], joker_slots=1)
    current = _composition(
        plan=_plan(strength=5.0),
        candidates=(_candidate("burnt_target_level", StrategyCommitment.FORMING, 5.0),),
    )
    stronger = _candidate("baron_mime_steel", StrategyCommitment.PINNED, 7.5)
    projected = _composition(
        plan=_plan("baron_mime_steel", StrategyCommitment.PINNED, 7.5),
        pinned="baron_mime_steel",
        candidates=(stronger,),
    )
    with patch(
        "games.balatro.forming_strategy_retention_policy.evaluate_bond_composition",
        side_effect=[((), current), ((), projected)],
    ), patch(
        "games.balatro.forming_strategy_retention_policy.projected_state_with_jokers",
        return_value=object(),
    ):
        result = apply_forming_strategy_retention(state, RandomJoker(), _Decision())

    assert result.action == REPLACE
    assert any("forming strategy pivot allowed" in note for note in result.rationale)
