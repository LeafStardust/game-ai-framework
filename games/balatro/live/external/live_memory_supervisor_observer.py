from __future__ import annotations

from time import monotonic, sleep

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    LiveMemoryObservationError,
    _integer,
    _string,
    _table_fields,
)


DEFAULT_NATIVE_READINESS_TIMEOUT_SECONDS = 20.0
DEFAULT_NATIVE_READINESS_POLL_SECONDS = 0.05
# Backward-compatible names retained for tests/callers that configured the
# original BLIND_SELECT-only readiness wrapper.
DEFAULT_BLIND_SELECT_READINESS_TIMEOUT_SECONDS = DEFAULT_NATIVE_READINESS_TIMEOUT_SECONDS
DEFAULT_BLIND_SELECT_READINESS_POLL_SECONDS = DEFAULT_NATIVE_READINESS_POLL_SECONDS


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


def _native_card_area_ready(decoder, value) -> bool:
    if value is None or value.kind != "table":
        return False
    area = _table_fields(decoder, value)
    cards = area.get("cards")
    if cards is None or cards.kind != "table":
        return False
    config = _table_fields(decoder, area.get("config"))
    return _integer(config.get("card_limit"), 0) > 0


def native_shop_ready(decoder, root) -> bool:
    """Return whether Balatro's native shop card areas are action-ready.

    Balatro can publish ``STATE=SHOP`` / ``STATE_COMPLETE=true`` before the shop
    CardArea objects have finished being created. In that window the public
    observer normalizes absent areas to empty ``limit=0`` collections, which can
    make the policy immediately choose END_SHOP. Calling ``toggle_shop`` that
    early may be accepted but fail to advance to BLIND_SELECT. Wait for the real
    native areas instead of relying on strategic card counts.

    Card counts are intentionally not part of readiness: an area can legitimately
    become empty after purchases. The CardArea, its cards table, and its positive
    configured capacity must exist for each normal shop surface.
    """
    return all(
        _native_card_area_ready(decoder, root.get(name))
        for name in ("shop_jokers", "shop_vouchers", "shop_booster")
    )


class SupervisorLiveMemoryBalatroObserver(LiveMemoryBalatroObserver):
    """Live observer that withholds public checkpoints before native UI readiness.

    This is intentionally supervisor-specific. Generic diagnostics still expose
    the earliest authoritative public snapshot, while the long-lived autonomous
    controller waits until Balatro has created the native objects required by the
    next first-party action. This covers restart-time BLIND_SELECT and the short
    post-cash-out SHOP construction window.
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
        shop_readiness_timeout_seconds: float | None = None,
        shop_readiness_poll_seconds: float | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if blind_select_readiness_timeout_seconds <= 0:
            raise ValueError("blind-select readiness timeout must be positive")
        if blind_select_readiness_poll_seconds < 0:
            raise ValueError("blind-select readiness poll interval cannot be negative")

        if shop_readiness_timeout_seconds is None:
            shop_readiness_timeout_seconds = blind_select_readiness_timeout_seconds
        if shop_readiness_poll_seconds is None:
            shop_readiness_poll_seconds = blind_select_readiness_poll_seconds
        if shop_readiness_timeout_seconds <= 0:
            raise ValueError("shop readiness timeout must be positive")
        if shop_readiness_poll_seconds < 0:
            raise ValueError("shop readiness poll interval cannot be negative")

        self.blind_select_readiness_timeout_seconds = float(
            blind_select_readiness_timeout_seconds
        )
        self.blind_select_readiness_poll_seconds = float(
            blind_select_readiness_poll_seconds
        )
        self.shop_readiness_timeout_seconds = float(shop_readiness_timeout_seconds)
        self.shop_readiness_poll_seconds = float(shop_readiness_poll_seconds)

    def _wait_for_native_readiness(
        self,
        snapshot,
        *,
        phase: str,
        ready,
        timeout_seconds: float,
        poll_seconds: float,
        timeout_message: str,
    ):
        deadline = monotonic() + timeout_seconds
        while True:
            decoder, _, root = self._root()
            if ready(decoder, root):
                # Re-observe after the native readiness check so the returned
                # public checkpoint is contemporaneous with the actionable UI.
                return super().observe()

            if monotonic() >= deadline:
                raise LiveMemoryObservationError(timeout_message)
            if poll_seconds:
                sleep(poll_seconds)

            snapshot = super().observe()
            if str(snapshot.phase) != phase or not snapshot.state_complete:
                return snapshot

    def observe(self):
        snapshot = super().observe()
        phase = str(snapshot.phase)
        if not snapshot.state_complete:
            return snapshot

        if phase == "BLIND_SELECT":
            return self._wait_for_native_readiness(
                snapshot,
                phase=phase,
                ready=native_blind_select_ready,
                timeout_seconds=self.blind_select_readiness_timeout_seconds,
                poll_seconds=self.blind_select_readiness_poll_seconds,
                timeout_message=(
                    "BLIND_SELECT became public-state stable but Balatro's native "
                    "blind-selection controls did not become ready before timeout"
                ),
            )

        if phase == "SHOP":
            return self._wait_for_native_readiness(
                snapshot,
                phase=phase,
                ready=native_shop_ready,
                timeout_seconds=self.shop_readiness_timeout_seconds,
                poll_seconds=self.shop_readiness_poll_seconds,
                timeout_message=(
                    "SHOP became public-state stable but Balatro's native shop "
                    "card areas did not become ready before timeout"
                ),
            )

        return snapshot
