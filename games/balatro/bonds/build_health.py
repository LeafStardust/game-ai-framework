from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable

from games.balatro.bonds.composer import Composition
from games.balatro.bonds.model import BondDevelopment, BondRealization
from games.balatro.bonds.motifs import MotifState, REALIZATION_STRENGTH
from games.balatro.bonds.score_projection import ScoreProjection


class BuildHealthState(StrEnum):
    COLLAPSING = "COLLAPSING"
    FRAGILE = "FRAGILE"
    STABLE = "STABLE"
    STRONG = "STRONG"
    DOMINANT = "DOMINANT"


@dataclass(frozen=True)
class BuildHealth:
    state: BuildHealthState
    score_pressure: float
    realization_ratio: float
    mature_ratio: float
    active_motif_count: int
    mature_motif_count: int
    economy_runway: float
    scaling_runway: float
    coherence_score: float
    reasons: tuple[str, ...]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _number(state: Any, names: tuple[str, ...], default: float = 0.0) -> float:
    for name in names:
        value = getattr(state, name, None)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return float(default)


def _realization_stats(developments: Iterable[BondDevelopment], composition: Composition) -> tuple[float, float]:
    selected = set(composition.bond_ids)
    devs = [d for d in developments if d.bond_id in selected]
    if not devs:
        return 0.0, 0.0
    active = sum(1 for d in devs if REALIZATION_STRENGTH[d.realization] >= REALIZATION_STRENGTH[BondRealization.ACTIVE])
    mature = sum(1 for d in devs if d.realization == BondRealization.MATURE)
    return active / len(devs), mature / len(devs)


def _economy_runway(state: Any) -> float:
    money = _number(state, ("money", "dollars", "cash"), 0.0)
    # $25 is the basic interest cap reference; more money still helps shop freedom.
    return _clamp01(money / 50.0)


def _scaling_runway(state: Any) -> float:
    ante = _number(state, ("ante",), 1.0)
    rounds = _number(state, ("rounds_remaining_estimate", "runway_rounds"), max(0.0, 8.0 - ante))
    return _clamp01(rounds / 5.0)


def evaluate_build_health(
    state: Any,
    *,
    developments: Iterable[BondDevelopment],
    composition: Composition,
    projection: ScoreProjection,
) -> BuildHealth:
    """Evaluate survivability and scaling without converting Bond rank into score.

    Score adequacy comes only from ``ScoreProjection``. Bond realization,
    composition, motifs, economy and runway influence confidence/stability, not
    chip totals.
    """
    developments = tuple(developments)
    realization_ratio, mature_ratio = _realization_stats(developments, composition)
    active_motifs = sum(1 for m in composition.motifs if m.state >= MotifState.ACTIVE)
    mature_motifs = sum(1 for m in composition.motifs if m.state == MotifState.MATURE)
    economy = _economy_runway(state)
    scaling = _scaling_runway(state)

    ratio = projection.expected_clear_ratio
    if projection.clear_probability is not None:
        probability = projection.clear_probability
    else:
        # This is only a health confidence proxy when search probability is absent.
        probability = _clamp01((ratio - 0.60) / 0.60)

    score_pressure = _clamp01(1.0 - min(1.0, ratio))

    reasons: list[str] = []
    if projection.ceiling_margin < 0:
        reasons.append("ceiling_projection_cannot_clear")
    elif projection.expected_margin < 0:
        reasons.append("expected_projection_below_blind")
    elif not projection.conservative_clear:
        reasons.append("clear_requires_above_conservative_output")
    else:
        reasons.append("conservative_projection_clears")

    if realization_ratio < 0.5:
        reasons.append("selected_bonds_weakly_realized")
    elif realization_ratio >= 0.8:
        reasons.append("selected_bonds_well_realized")

    if active_motifs:
        reasons.append("active_motif_support")
    if economy < 0.25:
        reasons.append("low_shop_runway")
    if scaling < 0.25:
        reasons.append("limited_scaling_runway")

    # Classification is dominated by actual score adequacy. Structural signals
    # can upgrade/downgrade confidence by at most one broad tier.
    if projection.ceiling_margin < 0 or probability < 0.15:
        health = BuildHealthState.COLLAPSING
    elif projection.expected_margin < 0 or probability < 0.40:
        health = BuildHealthState.FRAGILE
    elif projection.expected_clear_ratio < 1.35 or probability < 0.70:
        health = BuildHealthState.STABLE
    elif projection.expected_clear_ratio < 2.0:
        health = BuildHealthState.STRONG
    else:
        health = BuildHealthState.DOMINANT

    # Structural fragility can downgrade one tier, but cannot manufacture score.
    if realization_ratio < 0.35 and health in (BuildHealthState.DOMINANT, BuildHealthState.STRONG):
        health = BuildHealthState.STABLE
    elif realization_ratio < 0.35 and health == BuildHealthState.STABLE:
        health = BuildHealthState.FRAGILE

    # Mature coherent motifs can stabilize a marginal but clearing build, never
    # rescue a projection that does not clear in expectation.
    if projection.expected_clear and mature_motifs and health == BuildHealthState.STABLE:
        health = BuildHealthState.STRONG

    return BuildHealth(
        state=health,
        score_pressure=score_pressure,
        realization_ratio=realization_ratio,
        mature_ratio=mature_ratio,
        active_motif_count=active_motifs,
        mature_motif_count=mature_motifs,
        economy_runway=economy,
        scaling_runway=scaling,
        coherence_score=composition.coherence_score,
        reasons=tuple(dict.fromkeys(reasons)),
    )
