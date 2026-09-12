from dataclasses import FrozenInstanceError, replace
import json

import pytest

from games.balatro.env.promotion_contract import (
    B0_PROMOTION_CONTRACT,
    B0_PROMOTION_CONTRACT_VERSION,
    PRIMARY_PROMOTION_METRIC,
    FIXED_HOLDOUT_RULE,
    SECONDARY_REGRESSION_SCOPE,
    UNSEEDED_SUPERIORITY_RULE,
    ZERO_TOLERANCE_PATHOLOGIES,
    B0PromotionContractError,
    approximate_two_arm_power,
    required_two_arm_sample_size,
)
from games.balatro.env.seeded_evaluation import EVALUATED_BASELINE_VERSIONS


def test_env_b0_promotion_design_is_frozen_before_training_results():
    contract = B0_PROMOTION_CONTRACT

    assert contract.version == B0_PROMOTION_CONTRACT_VERSION
    assert contract.comparison_baselines == EVALUATED_BASELINE_VERSIONS
    assert contract.primary_metric == PRIMARY_PROMOTION_METRIC == "ante_8_clear_rate"
    assert contract.fixed_holdout_episodes_per_arm == 64
    assert contract.unseeded_manifests_per_arm == 4
    assert contract.unseeded_episodes_per_arm == 256
    assert contract.one_sided_alpha == 0.05
    assert contract.target_power == 0.80
    assert contract.power_reference_baseline_clear_rate == 0.20
    assert contract.minimum_detectable_clear_rate_improvement == 0.10
    assert contract.minimum_candidate_clear_rate == 0.20
    assert contract.minimum_unseeded_clear_rate_delta == 0.05
    assert contract.unseeded_superiority_rule == UNSEEDED_SUPERIORITY_RULE
    assert contract.fixed_holdout_rule == FIXED_HOLDOUT_RULE
    assert contract.secondary_regression_scope == SECONDARY_REGRESSION_SCOPE
    assert contract.require_unseeded_confidence_superiority is True
    assert contract.require_fixed_clear_nonregression is True


def test_env_b0_power_design_requires_231_and_plans_256_episodes_per_arm():
    contract = B0_PROMOTION_CONTRACT

    assert required_two_arm_sample_size(0.20, 0.30) == 231
    assert contract.required_power_sample_per_arm == 231
    assert contract.approximate_planned_power == pytest.approx(0.8350843138562211)
    assert contract.approximate_planned_power >= contract.target_power
    assert approximate_two_arm_power(256, 0.20, 0.30) == pytest.approx(
        contract.approximate_planned_power
    )


def test_env_b0_secondary_regression_and_pathology_gates_are_explicit():
    contract = B0_PROMOTION_CONTRACT

    assert contract.maximum_mean_ante_regression == 0.25
    assert contract.maximum_mean_requirement_progress_regression == 0.05
    assert contract.maximum_mean_minimum_money_regression == 2.0
    assert contract.maximum_mean_terminal_money_regression == 2.0
    assert contract.zero_tolerance_pathologies == ZERO_TOLERANCE_PATHOLOGIES
    assert "unsupported_mechanic" in contract.zero_tolerance_pathologies
    assert "illegal_action" in contract.zero_tolerance_pathologies
    assert "seed_provenance_mismatch" in contract.zero_tolerance_pathologies


def test_env_b0_promotion_contract_serialization_is_canonical_and_immutable():
    first = B0_PROMOTION_CONTRACT.to_json()
    payload = json.loads(first)

    assert first == B0_PROMOTION_CONTRACT.to_json()
    assert payload["required_power_sample_per_arm"] == 231
    assert payload["approximate_planned_power"] == pytest.approx(0.8350843138562211)
    with pytest.raises(FrozenInstanceError):
        B0_PROMOTION_CONTRACT.target_power = 0.5


@pytest.mark.parametrize(
    "changes",
    [
        {"version": "unknown"},
        {"comparison_baselines": tuple(reversed(EVALUATED_BASELINE_VERSIONS))},
        {"primary_metric": "mean_ante_reached"},
        {"unseeded_superiority_rule": "point_estimate_only"},
        {"fixed_holdout_episodes_per_arm": 63},
        {"unseeded_manifests_per_arm": 3, "unseeded_episodes_per_arm": 192},
        {"unseeded_episodes_per_arm": 255},
        {"target_power": 0.0},
        {"target_power": 0.90},
        {"minimum_detectable_clear_rate_improvement": 0.80},
        {"require_fixed_clear_nonregression": False},
        {"maximum_mean_ante_regression": -0.01},
        {"zero_tolerance_pathologies": ()},
    ],
)
def test_env_b0_promotion_contract_drift_fails_closed(changes):
    with pytest.raises(B0PromotionContractError):
        replace(B0_PROMOTION_CONTRACT, **changes)


@pytest.mark.parametrize(
    "args",
    [
        (0.2, 0.2),
        (0.3, 0.2),
        (-0.1, 0.2),
        (0.2, 1.1),
    ],
)
def test_env_b0_power_helpers_reject_invalid_rates(args):
    with pytest.raises(B0PromotionContractError):
        required_two_arm_sample_size(*args)
    with pytest.raises(B0PromotionContractError):
        approximate_two_arm_power(256, *args)
