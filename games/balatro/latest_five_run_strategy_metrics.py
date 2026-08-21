from __future__ import annotations

"""Five-run telemetry calibration for strategy strength and Build Health metrics.

Throwback is statically Silver until public skip scaling is realized. Its dynamic
Silver->Gold promotion is resolved by ``conditional_joker_relationship`` rather
than by monkey-patching private tracker assessment methods. This keeps flat,
state-aware, and tree-aware trackers on one non-recursive assessment path.
"""

from copy import copy
from dataclasses import replace

from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.strategy import BRONZE, GOLD, SILVER, BalatroStrategyTracker


_THROWBACK = "throwback"
_THROWBACK_TOKENS = frozenset({"throwback", "throwbackjoker"})


def _static_throwback(definition):
    return replace(
        definition,
        gold_jokers=frozenset(set(definition.gold_jokers) - set(_THROWBACK_TOKENS)),
        silver_jokers=frozenset(set(definition.silver_jokers) | set(_THROWBACK_TOKENS)),
        bronze_jokers=frozenset(set(definition.bronze_jokers) - set(_THROWBACK_TOKENS)),
    )


def install_latest_five_run_strategy_metrics() -> None:
    if getattr(BalatroStrategyTracker, "_latest_five_run_strategy_metrics_installed", False):
        return

    original_init = BalatroStrategyTracker.__init__

    def __init__(self, definitions, *args, **kwargs):
        calibrated = dict(definitions)
        if _THROWBACK in calibrated:
            calibrated[_THROWBACK] = _static_throwback(calibrated[_THROWBACK])
        original_init(self, calibrated, *args, **kwargs)

    BalatroStrategyTracker.__init__ = __init__
    BalatroStrategyTracker._latest_five_run_strategy_metrics_installed = True

    original_coherence = RuntimeBuildHealthEvaluator._coherence

    def _coherence(self, state, tracker):
        if tracker is None:
            return original_coherence(self, state, tracker)
        try:
            # The component index is a MappingProxyType; deepcopy is unsafe. A
            # shallow tracker clone preserves immutable catalogue/topology state
            # while isolating the two mutable shortlist-history fields used by
            # observe().
            working = copy(tracker)
            working._last_dominant_strategy_id = getattr(
                tracker, "_last_dominant_strategy_id", None
            )
            working._last_relevant_strategy_ids = tuple(
                getattr(tracker, "_last_relevant_strategy_ids", ()) or ()
            )

            resolution = working.observe(state)
            dominant_id = getattr(resolution, "dominant_strategy_id", None)
            if dominant_id is None:
                return 0.35
            getter = getattr(working, "primary_strategy_id", None)
            if callable(getter):
                dominant_id = getter(resolution) or dominant_id
            assessment = resolution.assessment(dominant_id)
            score = (
                max(0.0, float(getattr(assessment, "score", 0.0) or 0.0))
                if assessment is not None
                else 0.0
            )
            config = working._config(state)
            commit_floor = max(
                1e-9,
                working._number(config, "commit_threshold", 10.0),
            )
            score_ratio = min(1.0, score / commit_floor)
            jokers = tuple(getattr(state, "jokers", ()) or ())
            shortlist = tuple(getattr(resolution, "shortlist_strategy_ids", ()) or ())
            aligned = 0
            for joker in jokers:
                try:
                    relation = working.evaluate_item(state, joker, kind="JOKER")
                except (AttributeError, KeyError, TypeError, ValueError):
                    continue
                if (
                    bool(getattr(relation, "active_alignment", False))
                    and getattr(relation, "strategy_id", None) in shortlist
                    and getattr(relation, "tier", None) in {GOLD, SILVER, BRONZE}
                ):
                    aligned += 1
            aligned_ratio = aligned / len(jokers) if jokers else 0.0
            return min(1.0, score_ratio * 0.60 + aligned_ratio * 0.40)
        except (AttributeError, KeyError, TypeError, ValueError, RecursionError):
            return original_coherence(self, state, tracker)

    RuntimeBuildHealthEvaluator._coherence = _coherence
    RuntimeBuildHealthEvaluator._latest_five_run_strategy_metrics_installed = True
