from __future__ import annotations

"""Make ROUND_EVAL cash-out event-driven instead of delay-driven.

The generic supervisor quiet gate is useful for phases where an action can interrupt
an in-flight native transition. ROUND_EVAL is different: once Balatro's actual
``G.round_eval`` UI exists and ``G.FUNCS.cash_out`` is callable, the checkout action
is already native-ready. Waiting for another full-state quiet second only delays the
button press.

This installer narrows the exception to ROUND_EVAL. Other phases keep their existing
native-readiness and quiescence contracts unchanged.
"""

from .live_memory_supervisor_observer import SupervisorLiveMemoryBalatroObserver


_INSTALLED_ATTR = "_round_eval_checkout_fastpath_installed"


def _round_eval_ui_ready(root) -> bool:
    value = root.get("round_eval")
    return value is not None and value.kind in {"table", "userdata"}


def install_round_eval_checkout_fastpath() -> None:
    if getattr(SupervisorLiveMemoryBalatroObserver, _INSTALLED_ATTR, False):
        return

    original_wait_for_native_readiness = (
        SupervisorLiveMemoryBalatroObserver._wait_for_native_readiness
    )
    original_wait_for_full_state_quiet = (
        SupervisorLiveMemoryBalatroObserver._wait_for_full_state_quiet
    )

    def wait_for_native_readiness(
        self,
        snapshot,
        *,
        phase: str,
        ready,
        timeout_seconds: float,
        poll_seconds: float,
        timeout_message: str,
    ):
        if str(phase) != "ROUND_EVAL":
            return original_wait_for_native_readiness(
                self,
                snapshot,
                phase=phase,
                ready=ready,
                timeout_seconds=timeout_seconds,
                poll_seconds=poll_seconds,
                timeout_message=timeout_message,
            )

        def round_eval_ready(decoder, root) -> bool:
            return _round_eval_ui_ready(root) and bool(ready(decoder, root))

        return original_wait_for_native_readiness(
            self,
            snapshot,
            phase=phase,
            ready=round_eval_ready,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
            timeout_message=(
                "ROUND_EVAL became public-state stable but Balatro's native "
                "round-eval checkout UI/cash-out callback did not become ready "
                "before timeout"
            ),
        )

    def wait_for_full_state_quiet(self, snapshot):
        if bool(getattr(snapshot, "state_complete", False)) and str(
            getattr(snapshot, "phase", "")
        ) == "ROUND_EVAL":
            return snapshot
        return original_wait_for_full_state_quiet(self, snapshot)

    SupervisorLiveMemoryBalatroObserver._wait_for_native_readiness = (
        wait_for_native_readiness
    )
    SupervisorLiveMemoryBalatroObserver._wait_for_full_state_quiet = (
        wait_for_full_state_quiet
    )
    setattr(SupervisorLiveMemoryBalatroObserver, _INSTALLED_ATTR, True)
