from __future__ import annotations

"""Diagnostic-only timing for the live SHOP observation pipeline.

This module does not change readiness, settlement, state, or decision semantics.
It records wall-clock time spent in the supervisor observer's public snapshot,
native-readiness, post-pack-settle, and quiet-gate stages. Every SHOP observer
profile accumulated since the previous autonomous decision is appended to that
next decision's notes so normal JSONL traces identify the expensive stage without
a separate profiler.
"""

from time import perf_counter

from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.runtime.live_memory_supervisor_observer import (
    SupervisorLiveMemoryBalatroObserver,
)


def _timed_stage(self, name: str, call, *args, **kwargs):
    started = perf_counter()
    try:
        return call(*args, **kwargs)
    finally:
        profile = getattr(self, "_active_shop_latency_profile", None)
        if isinstance(profile, dict):
            profile[f"{name}_seconds"] = float(
                profile.get(f"{name}_seconds", 0.0)
            ) + (perf_counter() - started)
            profile[f"{name}_calls"] = int(profile.get(f"{name}_calls", 0)) + 1


def install_shop_observer_latency_diagnostic() -> None:
    if getattr(
        SupervisorLiveMemoryBalatroObserver,
        "_shop_observer_latency_diagnostic_installed",
        False,
    ):
        return

    original_observe = SupervisorLiveMemoryBalatroObserver.observe
    original_observe_public = SupervisorLiveMemoryBalatroObserver._observe_public
    original_native_readiness = (
        SupervisorLiveMemoryBalatroObserver._wait_for_native_readiness
    )
    original_post_pack_settle = (
        SupervisorLiveMemoryBalatroObserver._wait_for_post_pack_visual_settle
    )
    original_quiet = SupervisorLiveMemoryBalatroObserver._wait_for_full_state_quiet
    original_decide = LiveMemoryInjectedSingleStepRunner.decide

    def observe_public(self):
        return _timed_stage(self, "public", original_observe_public, self)

    def wait_for_native_readiness(self, snapshot, **kwargs):
        return _timed_stage(
            self,
            "native_readiness",
            original_native_readiness,
            self,
            snapshot,
            **kwargs,
        )

    def wait_for_post_pack_visual_settle(self, snapshot):
        return _timed_stage(
            self,
            "post_pack_settle",
            original_post_pack_settle,
            self,
            snapshot,
        )

    def wait_for_full_state_quiet(self, snapshot):
        return _timed_stage(
            self,
            "quiet",
            original_quiet,
            self,
            snapshot,
        )

    def observe(self):
        started = perf_counter()
        profile = {
            "public_seconds": 0.0,
            "public_calls": 0,
            "native_readiness_seconds": 0.0,
            "native_readiness_calls": 0,
            "post_pack_settle_seconds": 0.0,
            "post_pack_settle_calls": 0,
            "quiet_seconds": 0.0,
            "quiet_calls": 0,
        }
        previous = getattr(self, "_active_shop_latency_profile", None)
        self._active_shop_latency_profile = profile
        try:
            snapshot = original_observe(self)
        finally:
            self._active_shop_latency_profile = previous
        profile["total_seconds"] = perf_counter() - started
        profile["phase"] = str(getattr(snapshot, "phase", "UNKNOWN"))
        if profile["phase"] == "SHOP":
            profiles = getattr(self, "_shop_latency_profiles", None)
            if not isinstance(profiles, list):
                profiles = []
                self._shop_latency_profiles = profiles
            profiles.append(profile)
        return snapshot

    def decide(self):
        decision = original_decide(self)
        observer = getattr(self, "observer", None)
        profiles = getattr(observer, "_shop_latency_profiles", None)
        if not isinstance(profiles, list) or not profiles:
            return decision

        captured = tuple(profiles)
        profiles.clear()
        total = sum(float(item.get("total_seconds", 0.0)) for item in captured)
        public = sum(float(item.get("public_seconds", 0.0)) for item in captured)
        native = sum(
            float(item.get("native_readiness_seconds", 0.0)) for item in captured
        )
        settle = sum(
            float(item.get("post_pack_settle_seconds", 0.0)) for item in captured
        )
        quiet = sum(float(item.get("quiet_seconds", 0.0)) for item in captured)
        public_calls = sum(int(item.get("public_calls", 0)) for item in captured)

        diagnostic = (
            "shop_observer_latency="
            f"observations={len(captured)} "
            f"total={total:.3f}s "
            f"public={public:.3f}s/{public_calls}calls "
            f"native_readiness={native:.3f}s "
            f"post_pack_settle={settle:.3f}s "
            f"quiet={quiet:.3f}s"
        )
        return AutonomousStepDecision(
            snapshot=decision.snapshot,
            state=decision.state,
            action=decision.action,
            source=decision.source,
            notes=(*decision.notes, diagnostic),
            pack_signature=decision.pack_signature,
        )

    SupervisorLiveMemoryBalatroObserver._observe_public = observe_public
    SupervisorLiveMemoryBalatroObserver._wait_for_native_readiness = (
        wait_for_native_readiness
    )
    SupervisorLiveMemoryBalatroObserver._wait_for_post_pack_visual_settle = (
        wait_for_post_pack_visual_settle
    )
    SupervisorLiveMemoryBalatroObserver._wait_for_full_state_quiet = (
        wait_for_full_state_quiet
    )
    SupervisorLiveMemoryBalatroObserver.observe = observe
    LiveMemoryInjectedSingleStepRunner.decide = decide
    SupervisorLiveMemoryBalatroObserver._shop_observer_latency_diagnostic_installed = True


__all__ = ["install_shop_observer_latency_diagnostic"]
