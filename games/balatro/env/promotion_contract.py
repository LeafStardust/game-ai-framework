"""Frozen pre-training promotion and regression design for Red/White B0."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from typing import Any

from games.balatro.env.seeded_evaluation import (
    EVALUATED_BASELINE_VERSIONS,
    FIXED_SEEDED_EPISODE_COUNT,
)
from games.balatro.env.unseeded_evaluation import UNSEEDED_EPISODE_COUNT


B0_PROMOTION_CONTRACT_VERSION = "balatro-red-white-promotion-contract-v1"
PRIMARY_PROMOTION_METRIC = "ante_8_clear_rate"
UNSEEDED_SUPERIORITY_RULE = "candidate_one_sided_wilson_lower_gt_each_baseline_upper"
FIXED_HOLDOUT_RULE = "candidate_clear_count_gte_each_baseline"
SECONDARY_REGRESSION_SCOPE = "each_evidence_set_against_each_baseline"
ZERO_TOLERANCE_PATHOLOGIES = (
    "incomplete_episode",
    "nonterminal_episode",
    "illegal_action",
    "unsupported_mechanic",
    "schema_mismatch",
    "seed_provenance_mismatch",
    "diagnostic_provenance_mismatch",
)
_ONE_SIDED_95_Z = 1.6448536269514722
_EIGHTY_PERCENT_POWER_Z = 0.8416212335729143


class B0PromotionContractError(ValueError):
    """Raised when the pre-registered promotion design is internally invalid."""


def required_two_arm_sample_size(
    baseline_rate: float,
    candidate_rate: float,
    *,
    alpha_z: float = _ONE_SIDED_95_Z,
    power_z: float = _EIGHTY_PERCENT_POWER_Z,
) -> int:
    """Normal-approximation sample size per arm for a one-sided proportion test."""
    p0, p1 = float(baseline_rate), float(candidate_rate)
    if not 0.0 < p0 < p1 < 1.0:
        raise B0PromotionContractError("power rates must satisfy 0 < baseline < candidate < 1")
    if not math.isfinite(alpha_z) or not math.isfinite(power_z) or alpha_z <= 0.0 or power_z <= 0.0:
        raise B0PromotionContractError("power-design z values must be positive")
    pooled = (p0 + p1) / 2.0
    numerator = (
        alpha_z * math.sqrt(2.0 * pooled * (1.0 - pooled))
        + power_z * math.sqrt(p0 * (1.0 - p0) + p1 * (1.0 - p1))
    ) ** 2
    return math.ceil(numerator / ((p1 - p0) ** 2))


def approximate_two_arm_power(
    episodes_per_arm: int,
    baseline_rate: float,
    candidate_rate: float,
    *,
    alpha_z: float = _ONE_SIDED_95_Z,
) -> float:
    if isinstance(episodes_per_arm, bool) or not isinstance(episodes_per_arm, int):
        raise B0PromotionContractError("episodes per arm must be an exact integer")
    if episodes_per_arm <= 0:
        raise B0PromotionContractError("episodes per arm must be positive")
    p0, p1 = float(baseline_rate), float(candidate_rate)
    if not 0.0 < p0 < p1 < 1.0 or not math.isfinite(alpha_z) or alpha_z <= 0.0:
        raise B0PromotionContractError("invalid power-design inputs")
    pooled = (p0 + p1) / 2.0
    standard = math.sqrt(p0 * (1.0 - p0) + p1 * (1.0 - p1))
    z_value = (
        math.sqrt(episodes_per_arm) * (p1 - p0)
        - alpha_z * math.sqrt(2.0 * pooled * (1.0 - pooled))
    ) / standard
    return 0.5 * (1.0 + math.erf(z_value / math.sqrt(2.0)))


@dataclass(frozen=True)
class B0PromotionContract:
    version: str = B0_PROMOTION_CONTRACT_VERSION
    comparison_baselines: tuple[str, ...] = EVALUATED_BASELINE_VERSIONS
    primary_metric: str = PRIMARY_PROMOTION_METRIC
    fixed_holdout_episodes_per_arm: int = FIXED_SEEDED_EPISODE_COUNT
    unseeded_manifests_per_arm: int = 4
    unseeded_episodes_per_arm: int = 4 * UNSEEDED_EPISODE_COUNT
    one_sided_alpha: float = 0.05
    target_power: float = 0.80
    power_reference_baseline_clear_rate: float = 0.20
    minimum_detectable_clear_rate_improvement: float = 0.10
    minimum_candidate_clear_rate: float = 0.20
    minimum_unseeded_clear_rate_delta: float = 0.05
    unseeded_superiority_rule: str = UNSEEDED_SUPERIORITY_RULE
    fixed_holdout_rule: str = FIXED_HOLDOUT_RULE
    secondary_regression_scope: str = SECONDARY_REGRESSION_SCOPE
    require_unseeded_confidence_superiority: bool = True
    require_fixed_clear_nonregression: bool = True
    maximum_mean_ante_regression: float = 0.25
    maximum_mean_requirement_progress_regression: float = 0.05
    maximum_mean_minimum_money_regression: float = 2.0
    maximum_mean_terminal_money_regression: float = 2.0
    zero_tolerance_pathologies: tuple[str, ...] = ZERO_TOLERANCE_PATHOLOGIES

    def __post_init__(self) -> None:
        if self.version != B0_PROMOTION_CONTRACT_VERSION:
            raise B0PromotionContractError("promotion contract version mismatch")
        if self.comparison_baselines != EVALUATED_BASELINE_VERSIONS:
            raise B0PromotionContractError("promotion baselines must remain frozen")
        if self.primary_metric != PRIMARY_PROMOTION_METRIC:
            raise B0PromotionContractError("primary promotion metric must remain Ante 8 clear rate")
        if (
            self.unseeded_superiority_rule,
            self.fixed_holdout_rule,
            self.secondary_regression_scope,
        ) != (
            UNSEEDED_SUPERIORITY_RULE,
            FIXED_HOLDOUT_RULE,
            SECONDARY_REGRESSION_SCOPE,
        ):
            raise B0PromotionContractError("promotion comparison rules have drifted")
        for name in (
            "fixed_holdout_episodes_per_arm",
            "unseeded_manifests_per_arm",
            "unseeded_episodes_per_arm",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise B0PromotionContractError(f"{name} must be a positive exact integer")
        if self.fixed_holdout_episodes_per_arm != FIXED_SEEDED_EPISODE_COUNT:
            raise B0PromotionContractError("fixed holdout must use the complete frozen corpus")
        if self.unseeded_episodes_per_arm != (
            self.unseeded_manifests_per_arm * UNSEEDED_EPISODE_COUNT
        ):
            raise B0PromotionContractError("unseeded sample must contain complete manifests")
        if (self.unseeded_manifests_per_arm, self.unseeded_episodes_per_arm) != (4, 256):
            raise B0PromotionContractError("unseeded sample design is frozen at four manifests")
        for name in (
            "one_sided_alpha",
            "target_power",
            "power_reference_baseline_clear_rate",
            "minimum_detectable_clear_rate_improvement",
            "minimum_candidate_clear_rate",
            "minimum_unseeded_clear_rate_delta",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 < value < 1.0:
                raise B0PromotionContractError(f"{name} must be finite and within (0, 1)")
        if (
            self.one_sided_alpha,
            self.target_power,
            self.power_reference_baseline_clear_rate,
            self.minimum_detectable_clear_rate_improvement,
            self.minimum_candidate_clear_rate,
            self.minimum_unseeded_clear_rate_delta,
        ) != (0.05, 0.80, 0.20, 0.10, 0.20, 0.05):
            raise B0PromotionContractError("primary promotion design has drifted")
        if (
            self.require_unseeded_confidence_superiority is not True
            or self.require_fixed_clear_nonregression is not True
        ):
            raise B0PromotionContractError("primary promotion gates must remain enabled")
        candidate_rate = (
            self.power_reference_baseline_clear_rate
            + self.minimum_detectable_clear_rate_improvement
        )
        if candidate_rate >= 1.0:
            raise B0PromotionContractError("power-design candidate clear rate must be below 1")
        required = required_two_arm_sample_size(
            self.power_reference_baseline_clear_rate,
            candidate_rate,
        )
        if self.unseeded_episodes_per_arm < required:
            raise B0PromotionContractError(
                "unseeded sample is smaller than the pre-registered power design"
            )
        for name in (
            "maximum_mean_ante_regression",
            "maximum_mean_requirement_progress_regression",
            "maximum_mean_minimum_money_regression",
            "maximum_mean_terminal_money_regression",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise B0PromotionContractError(f"{name} must be finite and nonnegative")
        if (
            self.maximum_mean_ante_regression,
            self.maximum_mean_requirement_progress_regression,
            self.maximum_mean_minimum_money_regression,
            self.maximum_mean_terminal_money_regression,
        ) != (0.25, 0.05, 2.0, 2.0):
            raise B0PromotionContractError("secondary regression thresholds have drifted")
        if self.zero_tolerance_pathologies != ZERO_TOLERANCE_PATHOLOGIES:
            raise B0PromotionContractError("zero-tolerance pathology gates must remain frozen")

    @property
    def required_power_sample_per_arm(self) -> int:
        return required_two_arm_sample_size(
            self.power_reference_baseline_clear_rate,
            self.power_reference_baseline_clear_rate
            + self.minimum_detectable_clear_rate_improvement,
        )

    @property
    def approximate_planned_power(self) -> float:
        return approximate_two_arm_power(
            self.unseeded_episodes_per_arm,
            self.power_reference_baseline_clear_rate,
            self.power_reference_baseline_clear_rate
            + self.minimum_detectable_clear_rate_improvement,
        )

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["required_power_sample_per_arm"] = self.required_power_sample_per_arm
        value["approximate_planned_power"] = self.approximate_planned_power
        return value

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


B0_PROMOTION_CONTRACT = B0PromotionContract()
