from __future__ import annotations

"""Five-run telemetry calibration for strategy strength and Build Health metrics."""

from copy import copy
from dataclasses import is_dataclass, replace

from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.strategy import BRONZE, GOLD, SILVER, BalatroStrategyTracker


_THROWBACK = "throwback"
_THROWBACK_TOKENS = frozenset({"throwback", "throwbackjoker"})


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _item_tokens(item: object) -> frozenset[str]:
    values = (
        type(item).__name__,
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "ability_name", ""),
    )
    return frozenset(token for value in values if (token := _normalize(value)))


def _throwback_scaled(state) -> bool:
    for joker in getattr(state, "jokers", ()) or ():
        if not (_item_tokens(joker) & _THROWBACK_TOKENS):
            continue
        public = getattr(joker, "public_state", None)
        value = getattr(joker, "x_mult", None)
        if value is None and isinstance(public, dict):
            value = public.get("x_mult", 1.0)
        elif value is None and public is not None:
            value = getattr(public, "x_mult", 1.0)
        try:
            return float(value if value is not None else 1.0) > 1.0 + 1e-12
        except (TypeError, ValueError):
            return False
    return False


def _relationship_variant(definition, *, gold_jokers, silver_jokers, bronze_jokers):
    """Return one relationship-adjusted definition without assuming dataclass shape.

    Flat trackers use frozen StrategyDefinition dataclasses. Tree/state-aware layers
    may temporarily pass definition-like wrappers/proxies through ``_assess``. Those
    objects must not be fed to ``dataclasses.replace``. For mutable/copyable wrappers,
    clone and assign the three relationship sets; if the wrapper is intentionally
    immutable and exposes no supported replacement surface, leave it unchanged and
    let the underlying canonical definition remain authoritative.
    """
    values = {
        "gold_jokers": frozenset(gold_jokers),
        "silver_jokers": frozenset(silver_jokers),
        "bronze_jokers": frozenset(bronze_jokers),
    }
    if is_dataclass(definition) and not isinstance(definition, type):
        return replace(definition, **values)

    named_replace = getattr(definition, "_replace", None)
    if callable(named_replace):
        try:
            return named_replace(**values)
        except (TypeError, ValueError, AttributeError):
            pass

    try:
        cloned = copy(definition)
        for name, value in values.items():
            setattr(cloned, name, value)
        return cloned
    except (AttributeError, TypeError):
        return definition


def _static_throwback(definition):
    gold = set(getattr(definition, "gold_jokers", ()) or ()) - set(_THROWBACK_TOKENS)
    silver = set(getattr(definition, "silver_jokers", ()) or ()) | set(_THROWBACK_TOKENS)
    bronze = set(getattr(definition, "bronze_jokers", ()) or ()) - set(_THROWBACK_TOKENS)
    return _relationship_variant(
        definition,
        gold_jokers=gold,
        silver_jokers=silver,
        bronze_jokers=bronze,
    )


def _realized_throwback(definition, state):
    definition = _static_throwback(definition)
    if not _throwback_scaled(state):
        return definition
    gold = set(getattr(definition, "gold_jokers", ()) or ()) | set(_THROWBACK_TOKENS)
    silver = set(getattr(definition, "silver_jokers", ()) or ()) - set(_THROWBACK_TOKENS)
    bronze = set(getattr(definition, "bronze_jokers", ()) or ()) - set(_THROWBACK_TOKENS)
    return _relationship_variant(
        definition,
        gold_jokers=gold,
        silver_jokers=silver,
        bronze_jokers=bronze,
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

    original_assess_one = BalatroStrategyTracker._assess

    def _assess(self, state, definition):
        if getattr(definition, "strategy_id", None) == _THROWBACK:
            definition = _realized_throwback(definition, state)
        return original_assess_one(self, state, definition)

    BalatroStrategyTracker._assess = _assess

    original_evaluate_item = BalatroStrategyTracker.evaluate_item

    def evaluate_item(self, state, item, *, kind: str):
        result = original_evaluate_item(self, state, item, kind=kind)
        if str(kind).upper() != "JOKER" or not (_item_tokens(item) & _THROWBACK_TOKENS):
            return result
        if not _throwback_scaled(state):
            return result
        if getattr(result, "strategy_id", None) != _THROWBACK or getattr(result, "tier", None) == GOLD:
            return result

        resolution = self.observe(state)
        assessment = resolution.assessment(_THROWBACK)
        if assessment is None:
            return replace(
                result,
                tier=GOLD,
                rationale=(
                    *result.rationale,
                    "five-run calibration: realized Throwback skip scaling promotes the core Silver->Gold",
                ),
            )

        rank = next(
            (index for index, value in enumerate(resolution.assessments) if value.strategy_id == _THROWBACK),
            999,
        )
        scope = self._scope_factor(state, _THROWBACK, rank, resolution)
        config = self._config(state)
        pressure = self.strategy_pressure(state)
        alignment_scale = self._number(config, "candidate_alignment_scale", 0.08)
        relationship_delta = self.relationship_score(state, GOLD) - self.relationship_score(state, SILVER)
        alignment_delta = max(0.0, float(assessment.score)) * relationship_delta * scope
        value_delta = alignment_delta * alignment_scale * pressure
        projected_delta = relationship_delta * float(assessment.effectiveness)
        return replace(
            result,
            tier=GOLD,
            value=float(result.value) + value_delta,
            projected_score=float(result.projected_score) + projected_delta,
            rationale=(
                *result.rationale,
                "five-run calibration: realized Throwback skip scaling promotes the core Silver->Gold",
                f"conditional Gold alignment delta={value_delta:+.3f}",
            ),
        )

    BalatroStrategyTracker.evaluate_item = evaluate_item
    BalatroStrategyTracker._latest_five_run_strategy_metrics_installed = True

    original_coherence = RuntimeBuildHealthEvaluator._coherence

    def _coherence(self, state, tracker):
        if tracker is None:
            return original_coherence(self, state, tracker)
        try:
            # Trackers contain a MappingProxyType inverse component index, so a
            # deepcopy can fail and silently collapse coherence to the neutral 0.50
            # fallback. A shallow clone preserves the immutable catalogue/index and
            # subclass behavior while isolating observe()'s mutable history fields.
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
            score = max(0.0, float(getattr(assessment, "score", 0.0) or 0.0)) if assessment is not None else 0.0
            config = working._config(state)
            commit_floor = max(1e-9, working._number(config, "commit_threshold", 10.0))
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
        except (AttributeError, KeyError, TypeError, ValueError):
            return original_coherence(self, state, tracker)

    RuntimeBuildHealthEvaluator._coherence = _coherence
    RuntimeBuildHealthEvaluator._latest_five_run_strategy_metrics_installed = True
