from __future__ import annotations

"""Neutral compatibility adapter for the retired pre-Bond pack playstyle API.

The categorical PlaystyleIntent system no longer has strategic authority. Current
pack strategy influence is supplied by the Bond/composition StrategyPlan layers.
This module exists only as an import/constructor compatibility boundary while the
older runtime base class is being retired; it contributes exactly zero strategic
value.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetiredPlaystyleIntent:
    strengths: tuple[tuple[str, float], ...] = ()
    locked: bool = False
    lock_ante: int | None = None

    def strength(self, _playstyle) -> float:
        return 0.0


@dataclass(frozen=True)
class PackPlaystyleEvaluation:
    fit: float
    value: float
    intent: RetiredPlaystyleIntent
    ante: int
    rationale: tuple[str, ...]


class PackPlaystyleEvaluator:
    """Compatibility-only evaluator that deliberately contributes zero strategy value."""

    def __init__(self, *args, **kwargs) -> None:
        # Historical callers supplied profiler/intent_tracker. They are ignored on
        # purpose: retaining them would recreate the retired categorical authority.
        del args, kwargs

    def evaluate(
        self,
        state,
        *,
        kind: str,
        target=None,
        rank=None,
        suit=None,
    ) -> PackPlaystyleEvaluation:
        del kind, target, rank, suit
        return PackPlaystyleEvaluation(
            fit=0.0,
            value=0.0,
            intent=RetiredPlaystyleIntent(),
            ante=int(getattr(state, "ante", 0) or 0),
            rationale=(
                "legacy D9 playstyle authority retired; Bond/StrategyPlan owns strategic influence",
            ),
        )
