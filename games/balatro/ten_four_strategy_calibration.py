from __future__ import annotations

"""Telemetry-backed Ten-Four / Walkie Talkie relationship calibration.

A single Walkie Talkie is useful rank-specific additive scoring, but the latest
Red/White five-run batch showed that treating it as a standalone Gold core makes
Ten-Four commit immediately with weak realized output.  Even Steven directly
reinforces the same 10/4 rank package because both ranks are even.

Effective Red/White semantics:

* Walkie Talkie alone -> Silver.
* Even Steven alone -> Silver for Ten-Four.
* Walkie Talkie + Even Steven -> Walkie Talkie is promoted to Gold while
  Even Steven remains Silver.

This keeps the viable paired package while preventing one common Joker from
manufacturing a committed strategy by itself.
"""

from copy import copy
from dataclasses import is_dataclass, replace

from games.balatro.strategy import (
    GOLD,
    SILVER,
    BalatroStrategyTracker,
    build_component_strategy_index,
)


_TEN_FOUR = "ten_four"
_WALKIE = frozenset({"walkietalkie", "walkietalkiejoker"})
_EVEN = frozenset({"evensteven", "evenstevenjoker"})


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _item_tokens(item: object) -> frozenset[str]:
    values = (
        type(item).__name__,
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "ability_name", ""),
        getattr(item, "center", ""),
    )
    return frozenset(token for value in values if (token := _normalize(value)))


def _owned(state, tokens: frozenset[str]) -> bool:
    return any(_item_tokens(joker) & tokens for joker in getattr(state, "jokers", ()) or ())


def _relationship_variant(definition, *, gold_jokers, silver_jokers, bronze_jokers):
    """Return a relationship-adjusted definition for flat or tree-aware trackers."""
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


def _static_ten_four(definition):
    walkie_even = set(_WALKIE | _EVEN)
    gold = set(getattr(definition, "gold_jokers", ()) or ()) - walkie_even
    silver = set(getattr(definition, "silver_jokers", ()) or ()) | walkie_even
    bronze = set(getattr(definition, "bronze_jokers", ()) or ()) - walkie_even
    return _relationship_variant(
        definition,
        gold_jokers=gold,
        silver_jokers=silver,
        bronze_jokers=bronze,
    )


def _realized_ten_four(definition, state):
    definition = _static_ten_four(definition)
    if not (_owned(state, _WALKIE) and _owned(state, _EVEN)):
        return definition
    gold = set(getattr(definition, "gold_jokers", ()) or ()) | set(_WALKIE)
    silver = set(getattr(definition, "silver_jokers", ()) or ()) - set(_WALKIE)
    bronze = set(getattr(definition, "bronze_jokers", ()) or ()) - set(_WALKIE)
    return _relationship_variant(
        definition,
        gold_jokers=gold,
        silver_jokers=silver,
        bronze_jokers=bronze,
    )


def install_ten_four_strategy_calibration() -> None:
    if getattr(BalatroStrategyTracker, "_ten_four_strategy_calibration_installed", False):
        return

    original_init = BalatroStrategyTracker.__init__

    def __init__(self, definitions, *args, **kwargs):
        calibrated = dict(definitions)
        if _TEN_FOUR in calibrated:
            calibrated[_TEN_FOUR] = _static_ten_four(calibrated[_TEN_FOUR])
        original_init(self, calibrated, *args, **kwargs)
        # Keep the inverse index synchronized with the calibrated definitions even
        # for tracker subclasses that replace/extend definitions during init.
        self.component_index = build_component_strategy_index(self.definitions)

    BalatroStrategyTracker.__init__ = __init__

    original_assess_one = BalatroStrategyTracker._assess

    def _assess(self, state, definition):
        if getattr(definition, "strategy_id", None) == _TEN_FOUR:
            definition = _realized_ten_four(definition, state)
        return original_assess_one(self, state, definition)

    BalatroStrategyTracker._assess = _assess

    original_evaluate_item = BalatroStrategyTracker.evaluate_item

    def evaluate_item(self, state, item, *, kind: str):
        result = original_evaluate_item(self, state, item, kind=kind)
        if str(kind).upper() != "JOKER":
            return result
        if not (_item_tokens(item) & _WALKIE):
            return result
        if not (_owned(state, _WALKIE) and _owned(state, _EVEN)):
            return result
        if getattr(result, "strategy_id", None) != _TEN_FOUR:
            return result
        if getattr(result, "tier", None) == GOLD:
            return result

        # The static component index is deliberately Silver. When the paired
        # package is realized, expose the conditional Gold tier to downstream
        # component-role diagnostics and add the exact Gold-vs-Silver alignment
        # delta to candidate value rather than merely relabelling telemetry.
        resolution = self.observe(state)
        assessment = resolution.assessment(_TEN_FOUR)
        if assessment is None:
            return replace(
                result,
                tier=GOLD,
                rationale=(
                    *result.rationale,
                    "Ten-Four calibration: Walkie Talkie promoted Silver->Gold because Even Steven is owned",
                ),
            )

        rank = next(
            (index for index, value in enumerate(resolution.assessments) if value.strategy_id == _TEN_FOUR),
            999,
        )
        scope = self._scope_factor(state, _TEN_FOUR, rank, resolution)
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
                "Ten-Four calibration: Walkie Talkie promoted Silver->Gold because Even Steven is owned",
                f"conditional Gold alignment delta={value_delta:+.3f}; Even Steven remains Silver",
            ),
        )

    BalatroStrategyTracker.evaluate_item = evaluate_item
    BalatroStrategyTracker._ten_four_strategy_calibration_installed = True
