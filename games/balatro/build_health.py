from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EngineState(str, Enum):
    NOT_OWNED = "NOT_OWNED"
    OWNED_INACTIVE = "OWNED_INACTIVE"
    ACTIVATED_WEAK = "ACTIVATED_WEAK"
    ACTIVATED_HEALTHY = "ACTIVATED_HEALTHY"
    MATURE = "MATURE"


@dataclass(frozen=True)
class RealizedEngineStrength:
    engine_id: str
    state: EngineState
    current_strength: float = 0.0
    growth_rate: float = 0.0
    runway_need: float = 0.0
    rationale: tuple[str, ...] = ()

    @property
    def active(self) -> bool:
        return self.state not in {EngineState.NOT_OWNED, EngineState.OWNED_INACTIVE}


@dataclass(frozen=True)
class BuildHealthInputs:
    """Pure inputs for build-health evaluation.

    All normalized values are expected in the inclusive 0..1 range.  The model is
    intentionally detached from BalatroState so mechanics adapters can be tested
    independently and no health evaluation mutates live state.
    """

    survival_probability: float
    immediate_score_ratio: float
    scaling_ratio: float
    coherence_ratio: float
    runway_ratio: float
    engines: tuple[RealizedEngineStrength, ...] = ()


@dataclass(frozen=True)
class BuildHealth:
    total: float
    survival: float
    immediate: float
    scaling: float
    coherence: float
    runway: float
    critical: bool
    scaling_deficit: bool
    warnings: tuple[str, ...]
    engines: tuple[RealizedEngineStrength, ...]


@dataclass(frozen=True)
class BuildHealthWeights:
    survival: float = 0.30
    immediate: float = 0.20
    scaling: float = 0.25
    coherence: float = 0.15
    runway: float = 0.10

    def __post_init__(self) -> None:
        values = (self.survival, self.immediate, self.scaling, self.coherence, self.runway)
        if any(value < 0.0 for value in values):
            raise ValueError("Build Health weights cannot be negative")
        if sum(values) <= 0.0:
            raise ValueError("Build Health weights must have positive total mass")


class BuildHealthEvaluator:
    """Side-effect-free aggregate health model.

    The total is intentionally secondary to its dimensions.  A near-zero survival
    probability sets ``critical`` regardless of the weighted total, preventing a
    healthy long-term build from hiding an immediate losing state.
    """

    def __init__(
        self,
        *,
        weights: BuildHealthWeights | None = None,
        critical_survival_probability: float = 0.20,
        scaling_deficit_floor: float = 0.50,
        scaling_deficit_immediate_floor: float = 0.65,
    ) -> None:
        self.weights = weights or BuildHealthWeights()
        self.critical_survival_probability = self._clamp01(critical_survival_probability)
        self.scaling_deficit_floor = self._clamp01(scaling_deficit_floor)
        self.scaling_deficit_immediate_floor = self._clamp01(
            scaling_deficit_immediate_floor
        )

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _pct(value: float) -> float:
        return round(100.0 * value, 3)

    def evaluate(self, inputs: BuildHealthInputs) -> BuildHealth:
        survival = self._clamp01(inputs.survival_probability)
        immediate = self._clamp01(inputs.immediate_score_ratio)
        scaling = self._clamp01(inputs.scaling_ratio)
        coherence = self._clamp01(inputs.coherence_ratio)
        runway = self._clamp01(inputs.runway_ratio)

        weights = self.weights
        weight_total = (
            weights.survival
            + weights.immediate
            + weights.scaling
            + weights.coherence
            + weights.runway
        )
        weighted = (
            survival * weights.survival
            + immediate * weights.immediate
            + scaling * weights.scaling
            + coherence * weights.coherence
            + runway * weights.runway
        ) / weight_total

        critical = survival < self.critical_survival_probability
        scaling_deficit = (
            immediate >= self.scaling_deficit_immediate_floor
            and scaling < self.scaling_deficit_floor
        )

        warnings: list[str] = []
        if critical:
            warnings.append(
                f"critical survival deficit: clear probability={survival:.3f}"
            )
        if scaling_deficit:
            warnings.append(
                "scaling deficit: current output is serviceable but projected growth is behind schedule"
            )

        for engine in inputs.engines:
            if engine.state == EngineState.OWNED_INACTIVE:
                warnings.append(f"{engine.engine_id} — owned inactive engine")
            elif engine.state == EngineState.ACTIVATED_WEAK:
                warnings.append(f"{engine.engine_id} — activated but weak")

        return BuildHealth(
            total=self._pct(weighted),
            survival=self._pct(survival),
            immediate=self._pct(immediate),
            scaling=self._pct(scaling),
            coherence=self._pct(coherence),
            runway=self._pct(runway),
            critical=critical,
            scaling_deficit=scaling_deficit,
            warnings=tuple(warnings),
            engines=tuple(inputs.engines),
        )
