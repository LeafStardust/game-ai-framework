from __future__ import annotations

"""Keep SHOP settlement semantic instead of presentation-driven.

The supervisor's full-state quiet barrier intentionally includes UI/presentation
geometry. That is useful while waiting for transition-sensitive phases, but normal
shop cards may keep animating after the shop is already mechanically actionable.
Requiring one full second of an identical presentation fingerprint can therefore
starve the next SHOP decision indefinitely.

This policy preserves native SHOP readiness and only changes the final quiet test:
SHOP checkpoints are compared with ``ui`` fields stripped recursively. Real changes
in money, offers, owned Jokers, consumables, vouchers, boosters, or any other public
semantic state still reset the quiet window. Other phases retain the original full-
state barrier.
"""

from time import monotonic, sleep

from games.balatro.live.runtime.live_memory_observer import LiveMemoryObservationError
from games.balatro.live.runtime.live_memory_supervisor_observer import (
    SupervisorLiveMemoryBalatroObserver,
)
from games.balatro.shop_observer_latency_diagnostic import (
    install_shop_observer_latency_diagnostic,
)


def _semantic_payload(value):
    if isinstance(value, dict):
        return {
            key: _semantic_payload(item)
            for key, item in value.items()
            if key != "ui"
        }
    if isinstance(value, list):
        return [_semantic_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_semantic_payload(item) for item in value)
    return value


def shop_semantic_signature(snapshot) -> tuple:
    return (
        str(getattr(snapshot, "phase", "")),
        bool(getattr(snapshot, "state_complete", False)),
        _semantic_payload(getattr(snapshot, "payload", {}) or {}),
    )


def install_shop_semantic_quiet_policy() -> None:
    if getattr(
        SupervisorLiveMemoryBalatroObserver,
        "_shop_semantic_quiet_policy_installed",
        False,
    ):
        install_shop_observer_latency_diagnostic()
        return

    original_wait = SupervisorLiveMemoryBalatroObserver._wait_for_full_state_quiet

    def wait_for_full_state_quiet(self, snapshot):
        if str(getattr(snapshot, "phase", "")) != "SHOP":
            return original_wait(self, snapshot)

        signature = shop_semantic_signature(snapshot)
        if (
            bool(getattr(snapshot, "state_complete", False))
            and getattr(self, "_last_quiescent_shop_semantic_signature", None)
            == signature
        ):
            return snapshot

        deadline = monotonic() + self.full_state_quiet_timeout_seconds
        last = snapshot
        last_signature = signature
        quiet_since = (
            monotonic() if bool(getattr(snapshot, "state_complete", False)) else None
        )

        while True:
            now = monotonic()
            if (
                quiet_since is not None
                and now - quiet_since >= self.full_state_quiet_seconds
            ):
                settled_signature = shop_semantic_signature(last)
                self._last_quiescent_shop_semantic_signature = settled_signature
                self._last_quiescent_sequence = int(last.sequence)
                return last

            if now >= deadline:
                raise LiveMemoryObservationError(
                    "Balatro SHOP semantic state did not remain quiet before "
                    "supervisor command readiness; "
                    f"sequence={last.sequence}, "
                    f"complete={bool(last.state_complete)}"
                )

            if self.full_state_quiet_poll_seconds:
                sleep(self.full_state_quiet_poll_seconds)
            current = self._observe_public()
            current_signature = shop_semantic_signature(current)

            if (
                current_signature != last_signature
                or not bool(getattr(current, "state_complete", False))
            ):
                last_signature = current_signature
                quiet_since = (
                    monotonic()
                    if bool(getattr(current, "state_complete", False))
                    else None
                )
            elif quiet_since is None and bool(getattr(current, "state_complete", False)):
                quiet_since = monotonic()

            last = current

    SupervisorLiveMemoryBalatroObserver._wait_for_full_state_quiet = (
        wait_for_full_state_quiet
    )
    SupervisorLiveMemoryBalatroObserver._shop_semantic_quiet_policy_installed = True
    install_shop_observer_latency_diagnostic()


__all__ = [
    "install_shop_semantic_quiet_policy",
    "shop_semantic_signature",
]
