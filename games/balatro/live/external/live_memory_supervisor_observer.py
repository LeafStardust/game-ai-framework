from __future__ import annotations

from time import monotonic, sleep

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    LiveMemoryObservationError,
    _string,
    _table_fields,
)


DEFAULT_BLIND_SELECT_READINESS_TIMEOUT_SECONDS = 20.0
DEFAULT_BLIND_SELECT_READINESS_POLL_SECONDS = 0.05


def native_blind_select_ready(decoder, root) -> bool:
    """Return whether Balatro's native blind-select UI is actually actionable.

    ``STATE_COMPLETE`` and a stable public payload can precede creation of
    ``G.GAME.blind_on_deck`` / ``G.blind_select_opts`` immediately after a run
    restart. The injected executor correctly rejects SELECT_BLIND during that
    window, so the persistent supervisor must not treat the earlier snapshot as
    action-ready.
    """
    game = _table_fields(decoder, root.get("GAME"))
    blind_on_deck = _string(game.get("blind_on_deck"))
    if not blind_on_deck:
        return False

    opts_value = root.get("blind_select_opts")
    if opts_value is None or opts_value.kind != "table":
        return False
    try:
        opts = decoder.string_fields(int(opts_value.value))
    except (OSError, RuntimeError, ValueError, TypeError):
        return False

    pane = opts.get(str(blind_on_deck).lower())
    return pane is not None and pane.kind == "table"


class SupervisorLiveMemoryBalatroObserver(LiveMemoryBalatroObserver):
    """Live observer that withholds premature BLIND_SELECT checkpoints.

    This is intentionally supervisor-specific. Generic diagnostics still expose
    the earliest authoritative public snapshot, while the long-lived autonomous
    controller waits until Balatro has created the native blind-selection objects
    that the first-party bridge needs for SELECT_BLIND.
    """

    def __init__(
        self,
        *args,
        blind_select_readiness_timeout_seconds: float = (
            DEFAULT_BLIND_SELECT_READINESS_TIMEOUT_SECONDS
        ),
        blind_select_readiness_poll_seconds: float = (
            DEFAULT_BLIND_SELECT_READINESS_POLL_SECONDS
        ),
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if blind_select_readiness_timeout_seconds <= 0:
            raise ValueError("blind-select readiness timeout must be positive")
        if blind_select_readiness_poll_seconds < 0:
            raise ValueError("blind-select readiness poll interval cannot be negative")
        self.blind_select_readiness_timeout_seconds = float(
            blind_select_readiness_timeout_seconds
        )
        self.blind_select_readiness_poll_seconds = float(
            blind_select_readiness_poll_seconds
        )

    def observe(self):
        snapshot = super().observe()
        if str(snapshot.phase) != "BLIND_SELECT" or not snapshot.state_complete:
            return snapshot

        deadline = monotonic() + self.blind_select_readiness_timeout_seconds
        while True:
            decoder, _, root = self._root()
            if native_blind_select_ready(decoder, root):
                # Re-observe after the native readiness check so the returned
                # public checkpoint is contemporaneous with the actionable UI.
                return super().observe()

            if monotonic() >= deadline:
                raise LiveMemoryObservationError(
                    "BLIND_SELECT became public-state stable but Balatro's native "
                    "blind-selection controls did not become ready before timeout"
                )
            if self.blind_select_readiness_poll_seconds:
                sleep(self.blind_select_readiness_poll_seconds)

            snapshot = super().observe()
            if str(snapshot.phase) != "BLIND_SELECT" or not snapshot.state_complete:
                return snapshot
