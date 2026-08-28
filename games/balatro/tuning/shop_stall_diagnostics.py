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

    def emit(self, stage: str, status: str, *, elapsed_seconds: float | None = None) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "stage": str(stage),
            "status": str(status),
        }
        if elapsed_seconds is not None:
            payload["elapsed_seconds"] = round(float(elapsed_seconds), 6)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            handle.flush()

    def timed(self, stage: str, call: Callable, *args, **kwargs):
        started = perf_counter()
        self.emit(stage, "BEGIN")
        try:
            result = call(*args, **kwargs)
        except BaseException:
            self.emit(stage, "ERROR", elapsed_seconds=perf_counter() - started)
            raise
        self.emit(stage, "END", elapsed_seconds=perf_counter() - started)
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
