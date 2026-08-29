from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BALATRO = ROOT / "games" / "balatro"


def _source(name: str) -> str:
    return (BALATRO / name).read_text(encoding="utf-8")


def _call_attributes(source: str) -> set[str]:
    tree = ast.parse(source)
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def test_unopened_d8_expectations_do_not_enter_d9_pack_authority() -> None:
    for filename in (
        "arcana_booster_expectation_policy.py",
        "spectral_booster_expectation_policy.py",
    ):
        source = _source(filename)
        assert "BalatroPackPolicy" not in source
        assert "LivePackChoice" not in source
        assert "SELECT_PACK_CARD" not in source
        assert "score_action" not in _call_attributes(source)


def test_standard_unopened_expectation_uses_bounded_context_without_policy_recursion() -> None:
    source = _source("standard_booster_expectation_policy.py")
    calls = _call_attributes(source)

    # Standard's finite generator may reuse the bounded B6 feature graph and literal
    # deck-growth evaluator. The forbidden edge is policy recursion, not all context.
    assert "score_action" not in calls
    assert "rank_actions" not in calls
    assert "decide" not in calls
    assert "BuildAwareShopArbiter" not in source
    assert "BuildAwareShopRerollPolicy" not in source


def test_emperor_generated_outcomes_do_not_reenter_d9() -> None:
    source = _source("emperor_pack_expectation_policy.py")
    calls = _call_attributes(source)

    assert "score_action" not in calls
    assert "LivePackChoice" not in source
    assert "SELECT_PACK_CARD" not in source
    assert "UnopenedConsumableOutcomeValueEvaluator" in source


def test_future_tarot_reroll_expectation_does_not_enter_held_or_d9_authority() -> None:
    source = _source("reroll_tarot_guard_policy.py")
    calls = _call_attributes(source)

    assert "HeldConsumableOptionEvaluator" not in source
    assert "BalatroPackPolicy" not in source
    assert "score_action" not in calls
    assert "UnopenedConsumableOutcomeValueEvaluator" in source


def test_unopened_leaf_has_no_shop_or_pack_decision_edge() -> None:
    source = _source("unopened_consumable_outcome_value.py")
    calls = _call_attributes(source)

    assert "BalatroPackPolicy" not in source
    assert "BuildAwareShopArbiter" not in source
    assert "BuildAwareShopRerollPolicy" not in source
    assert "score_action" not in calls
    assert "decide" not in calls


def test_shop_runtime_bound_does_not_reintroduce_d8_visible_value_wrappers() -> None:
    source = _source("shop_expectation_runtime_bound_policy.py")

    assert "ArcanaBoosterExpectationEvaluator._visible_value =" not in source
    assert "SpectralBoosterExpectationEvaluator._visible_value =" not in source
