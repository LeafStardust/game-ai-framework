from __future__ import annotations

"""Diagnostic-only timing for the live SHOP pipeline.

This module does not change readiness, settlement, state, or decision semantics.
It records wall-clock time spent in the supervisor observer's public snapshot,
native-readiness, post-pack-settle, and quiet-gate stages. It also records the
single-step runner's total SHOP decision time and its existing observation,
translation, policy, and D14 child components.

The JSONL run logger writes observation/decision rows only after a successful live
transition has completed. Therefore adjacent event timestamps cannot be used to
infer policy latency. These explicit notes keep observer time and D14 policy time
separate in the durable trace.
"""

from time import perf_counter

from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.runtime.live_memory_supervisor_observer import (
    SupervisorLiveMemoryBalatroObserver,
)
from games.balatro.shop_policy_latency_diagnostic import (
    clear_shop_policy_latency_profile,
    consume_shop_policy_latency_note,
    install_shop_policy_latency_diagnostic,
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


def shop_decision_latency_note(runner, total_seconds: float) -> str:
    return (
        "shop_decision_latency="
        f"total={float(total_seconds):.3f}s "
        f"observation={float(getattr(runner, 'last_observation_seconds', 0.0)):.3f}s "
        f"translation={float(getattr(runner, 'last_translation_seconds', 0.0)):.3f}s "
        f"policy={float(getattr(runner, 'last_policy_seconds', 0.0)):.3f}s"
    )


def install_shop_observer_latency_diagnostic() -> None:
    install_shop_policy_latency_diagnostic()
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
        clear_shop_policy_latency_profile()
        started = perf_counter()
        decision = original_decide(self)
        decision_total = perf_counter() - started
        d14_note = consume_shop_policy_latency_note()
        if str(getattr(decision.snapshot, "phase", "")) != "SHOP":
            return decision

        observer = getattr(self, "observer", None)
        if not isinstance(observer, SupervisorLiveMemoryBalatroObserver):
            # The diagnostic is production-live telemetry, not decision semantics.
            # Unit/fake observers must see the exact notes emitted by the policy
            # under test instead of inheriting globally installed timing notes.
            return decision

        diagnostics: list[str] = []
        profiles = getattr(observer, "_shop_latency_profiles", None)
        if isinstance(profiles, list) and profiles:
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
            diagnostics.append(
                "shop_observer_latency="
                f"observations={len(captured)} "
                f"total={total:.3f}s "
                f"public={public:.3f}s/{public_calls}calls "
                f"native_readiness={native:.3f}s "
                f"post_pack_settle={settle:.3f}s "
                f"quiet={quiet:.3f}s"
            )

        diagnostics.append(shop_decision_latency_note(self, decision_total))
        if d14_note is not None:
            diagnostics.append(d14_note)

        # Preserve any non-dataclass diagnostic attributes attached by later
        # decision policies. Reconstructing the frozen dataclass here would silently
        # discard those attributes, so mutate only its diagnostic notes field.
        object.__setattr__(
            decision,
            "notes",
            (*tuple(getattr(decision, "notes", ())), *diagnostics),
        )
        return decision

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


__all__ = [
    "install_shop_observer_latency_diagnostic",
    "shop_decision_latency_note",
]
