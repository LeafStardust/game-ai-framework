from __future__ import annotations

"""Durable, diagnostic-only timing trace for live-tuning SHOP stalls.

The authoritative tuning evaluator uses the normal production supervisor/runner.
This module wraps selected existing call boundaries without changing decisions so a
manually interrupted tuner can still reveal the last SHOP sub-stage it entered.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable


class LiveTuningShopTrace:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def emit(
        self,
        stage: str,
        status: str,
        *,
        elapsed_seconds: float | None = None,
        **details,
    ) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "stage": str(stage),
            "status": str(status),
        }
        if elapsed_seconds is not None:
            payload["elapsed_seconds"] = round(float(elapsed_seconds), 6)
        payload.update(
            {
                str(key): value
                for key, value in details.items()
                if value is not None
            }
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            handle.flush()

    def timed(self, stage: str, call: Callable, *args, trace_details=None, **kwargs):
        details = dict(trace_details or {})
        started = perf_counter()
        self.emit(stage, "BEGIN", **details)
        try:
            result = call(*args, **kwargs)
        except BaseException:
            self.emit(
                stage,
                "ERROR",
                elapsed_seconds=perf_counter() - started,
                **details,
            )
            raise
        self.emit(
            stage,
            "END",
            elapsed_seconds=perf_counter() - started,
            **details,
        )
        return result


def _wrap_method(trace: LiveTuningShopTrace, target, name: str, stage: str) -> None:
    original = getattr(target, name, None)
    if not callable(original):
        return
    marker = f"_balatro_live_tuning_trace_{name}"
    if getattr(target, marker, False):
        return

    def wrapped(*args, **kwargs):
        return trace.timed(stage, original, *args, **kwargs)

    setattr(target, name, wrapped)
    setattr(target, marker, True)


def _booster_details(policy, action) -> dict[str, object]:
    target = getattr(action, "target", None)
    family = None
    variant = None
    try:
        family = policy._family(target)
    except (AttributeError, TypeError, ValueError):
        pass
    try:
        variant = policy._variant(target)
    except (AttributeError, TypeError, ValueError):
        pass
    label = None
    if isinstance(target, dict):
        label = target.get("label") or target.get("name") or target.get("center")
    elif target is not None:
        label = (
            getattr(target, "label", None)
            or getattr(target, "name", None)
            or getattr(target, "center", None)
        )
    return {
        "booster_family": str(family) if family is not None else None,
        "booster_variant": str(variant) if variant is not None else None,
        "booster_label": str(label) if label is not None else None,
    }


def _arcana_record_details(record) -> dict[str, object]:
    if not isinstance(record, dict):
        return {"arcana_record_type": type(record).__name__}
    return {
        "arcana_label": str(record.get("label") or record.get("ability_name") or ""),
        "arcana_center": str(record.get("center") or record.get("key") or ""),
        "arcana_set": str(record.get("ability_set") or record.get("set") or ""),
    }


def _wrap_arcana_visible_value(trace: LiveTuningShopTrace, evaluator) -> None:
    original = getattr(evaluator, "_visible_value", None)
    if not callable(original):
        return
    marker = "_balatro_live_tuning_trace_visible_value"
    if getattr(evaluator, marker, False):
        return

    def wrapped(state, record, *args, **kwargs):
        return trace.timed(
            "D8_ARCANA_VISIBLE_VALUE",
            original,
            state,
            record,
            *args,
            trace_details=_arcana_record_details(record),
            **kwargs,
        )

    setattr(evaluator, "_visible_value", wrapped)
    setattr(evaluator, marker, True)


def _wrap_booster_recommend(trace: LiveTuningShopTrace, policy) -> None:
    original = getattr(policy, "recommend", None)
    if not callable(original):
        return
    marker = "_balatro_live_tuning_trace_recommend"
    if getattr(policy, marker, False):
        return

    build_profiler = getattr(policy, "build_profiler", None)
    if build_profiler is not None:
        _wrap_method(trace, build_profiler, "profile", "D8_BUILD_PROFILE")

    for attribute, stage in (
        ("_standard_generator_expectation", "D8_STANDARD_EXPECTATION"),
        ("_arcana_generator_expectation", "D8_ARCANA_EXPECTATION"),
        ("_spectral_generator_expectation", "D8_SPECTRAL_EXPECTATION"),
    ):
        evaluator = getattr(policy, attribute, None)
        if evaluator is not None:
            if attribute == "_arcana_generator_expectation":
                _wrap_arcana_visible_value(trace, evaluator)
            _wrap_method(trace, evaluator, "evaluate", stage)

    def wrapped(state, action, *args, **kwargs):
        return trace.timed(
            "D14_BOOSTER_RECOMMEND",
            original,
            state,
            action,
            *args,
            trace_details=_booster_details(policy, action),
            **kwargs,
        )

    setattr(policy, "recommend", wrapped)
    setattr(policy, marker, True)


def _wrap_policy_factory(
    trace: LiveTuningShopTrace,
    arbiter,
    factory_name: str,
    factory_stage: str,
    recommend_stage: str,
) -> None:
    original = getattr(arbiter, factory_name, None)
    if not callable(original):
        return
    marker = f"_balatro_live_tuning_trace_{factory_name}"
    if getattr(arbiter, marker, False):
        return

    def wrapped(*args, **kwargs):
        policy = trace.timed(factory_stage, original, *args, **kwargs)
        if recommend_stage == "D14_BOOSTER_RECOMMEND":
            _wrap_booster_recommend(trace, policy)
        else:
            _wrap_method(trace, policy, "recommend", recommend_stage)
        return policy

    setattr(arbiter, factory_name, wrapped)
    setattr(arbiter, marker, True)


def instrument_live_tuning_shop_runner(runner, *, trace_path: str | Path):
    """Add durable timing markers to one normal production runner instance."""
    trace = LiveTuningShopTrace(trace_path)
    trace.emit("RUNNER_INSTRUMENTATION", "READY")

    _wrap_method(trace, runner, "_recommend_consumable_use", "SHOP_PRE_D14_CONSUMABLE_CHECK")
    _wrap_method(trace, runner.shop_generator, "generate_actions", "SHOP_ACTION_GENERATION")

    original_terms_reader = getattr(runner, "reroll_terms_reader", None)
    if callable(original_terms_reader):
        def traced_terms_reader():
            return trace.timed("SHOP_REROLL_TERMS_READ", original_terms_reader)

        runner.reroll_terms_reader = traced_terms_reader

    arbiter = runner.shop_arbiter
    _wrap_method(trace, arbiter, "_pending_bond_pair_completion", "D14_PENDING_BOND_PAIR")
    _wrap_method(trace, arbiter.shop_policy, "rank_actions", "D14_DETERMINISTIC_RANK")
    _wrap_method(trace, arbiter, "_best_joker_decision", "D14_JOKER")
    _wrap_method(trace, arbiter, "_best_consumable_decision", "D14_CONSUMABLE")
    _wrap_policy_factory(
        trace,
        arbiter,
        "_booster_policy_for_state",
        "D14_BOOSTER_POLICY_RESOLVE",
        "D14_BOOSTER_RECOMMEND",
    )
    _wrap_policy_factory(
        trace,
        arbiter,
        "_reroll_policy_for_state",
        "D14_REROLL_POLICY_RESOLVE",
        "D14_REROLL_RECOMMEND",
    )
    _wrap_method(trace, arbiter, "_best_visible_bond_pair", "D14_VISIBLE_BOND_PAIR")
    _wrap_method(trace, arbiter.utility_scale, "baseline_gain", "D14_UTILITY_BASELINE")
    _wrap_method(trace, arbiter.utility_scale, "joker_gain", "D14_UTILITY_JOKER")
    _wrap_method(trace, arbiter.utility_scale, "consumable_gain", "D14_UTILITY_CONSUMABLE")
    _wrap_method(trace, arbiter.utility_scale, "booster_gain", "D14_UTILITY_BOOSTER")
    _wrap_method(trace, arbiter, "decide", "D14_TOTAL")
    return runner


def install_live_tuning_shop_diagnostics(supervisor, *, trace_path: str | Path) -> bool:
    """Wrap runners created by a supervisor; return False for non-production fakes."""
    original_factory = getattr(supervisor, "runner_factory", None)
    if not callable(original_factory):
        return False

    def traced_runner_factory(observer):
        runner = original_factory(observer)
        return instrument_live_tuning_shop_runner(runner, trace_path=trace_path)

    supervisor.runner_factory = traced_runner_factory
    return True
