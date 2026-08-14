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
DEFAULT_POST_PACK_SETTLE_SECONDS = 0.50
DEFAULT_JOKER_VISUAL_STABLE_SECONDS = 0.25
DEFAULT_POST_PACK_SETTLE_TIMEOUT_SECONDS = 5.0
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


def _freeze_visual(value):
    if isinstance(value, dict):
        return tuple(
            (str(key), _freeze_visual(item))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        )
    if isinstance(value, list):
        return tuple(_freeze_visual(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_visual(item) for item in value)
    return value


def joker_visual_signature(snapshot) -> tuple[tuple, ...]:
    """Return only owned-Joker identity plus presentation geometry.

    The signature deliberately ignores strategic Joker state. It is used only to
    detect whether a Joker card is still physically moving after pack resolution;
    planner semantics continue to come from the ordinary public snapshot.
    """
    area = snapshot.payload.get("jokers")
    cards = area.get("cards") if isinstance(area, dict) else None
    if not isinstance(cards, list):
        return ()

    result = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        result.append(
            (
                card.get("live_id"),
                card.get("center"),
                card.get("label"),
                _freeze_visual(card.get("ui")),
            )
        )
    return tuple(result)


def _is_pack_phase(phase: str) -> bool:
    return str(phase).endswith("_PACK")


class SupervisorLiveMemoryBalatroObserver(LiveMemoryBalatroObserver):
    """Live observer that withholds public checkpoints before native UI readiness.

    This is intentionally supervisor-specific. Generic diagnostics still expose
    the earliest authoritative public snapshot, while the long-lived autonomous
    controller waits until Balatro has created the native objects required by the
    next first-party action. This covers restart-time BLIND_SELECT, the short
    post-cash-out SHOP construction window, and post-booster visual settlement so
    a newly acquired Joker is not interrupted while moving into its Joker area.
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
        post_pack_settle_seconds: float = DEFAULT_POST_PACK_SETTLE_SECONDS,
        joker_visual_stable_seconds: float = DEFAULT_JOKER_VISUAL_STABLE_SECONDS,
        post_pack_settle_timeout_seconds: float = (
            DEFAULT_POST_PACK_SETTLE_TIMEOUT_SECONDS
        ),
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
        if post_pack_settle_seconds < 0:
            raise ValueError("post-pack settle duration cannot be negative")
        if joker_visual_stable_seconds < 0:
            raise ValueError("joker visual stable duration cannot be negative")
        if post_pack_settle_timeout_seconds <= 0:
            raise ValueError("post-pack settle timeout must be positive")

        self.blind_select_readiness_timeout_seconds = float(
            blind_select_readiness_timeout_seconds
        )
        self.blind_select_readiness_poll_seconds = float(
            blind_select_readiness_poll_seconds
        )
        self.shop_readiness_timeout_seconds = float(shop_readiness_timeout_seconds)
        self.shop_readiness_poll_seconds = float(shop_readiness_poll_seconds)
        self.post_pack_settle_seconds = float(post_pack_settle_seconds)
        self.joker_visual_stable_seconds = float(joker_visual_stable_seconds)
        self.post_pack_settle_timeout_seconds = float(
            post_pack_settle_timeout_seconds
        )
        self._last_exposed_phase: str | None = None

    def _observe_public(self):
        return super().observe()

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
                return self._observe_public()

            if monotonic() >= deadline:
                raise LiveMemoryObservationError(timeout_message)
            if poll_seconds:
                sleep(poll_seconds)

            snapshot = self._observe_public()
            if str(snapshot.phase) != phase or not snapshot.state_complete:
                return snapshot

    def _wait_for_post_pack_visual_settle(self, snapshot):
        """Wait for pack-close events and owned-Joker movement to finish.

        Pack callbacks are asynchronous. Balatro may publish SHOP before the card
        selected from a Buffoon pack has finished entering ``G.jokers`` and moving
        to its final visual position. Exposing that first SHOP frame lets the next
        autonomous command interrupt the event sequence. Require both a short
        pack-resolution grace period and a continuously stable Joker geometry
        window; movement resets the stability clock instead of relying on one fixed
        sleep.
        """
        started = monotonic()
        deadline = started + self.post_pack_settle_timeout_seconds
        minimum_ready_at = started + self.post_pack_settle_seconds
        last = snapshot
        last_signature = joker_visual_signature(snapshot)
        visual_stable_since = started

        while True:
            now = monotonic()
            if (
                now >= minimum_ready_at
                and now - visual_stable_since >= self.joker_visual_stable_seconds
            ):
                return last
            if now >= deadline:
                raise LiveMemoryObservationError(
                    "booster pack returned to SHOP but owned-Joker presentation "
                    "did not settle before timeout"
                )

            if self.shop_readiness_poll_seconds:
                sleep(self.shop_readiness_poll_seconds)
            current = self._observe_public()
            last = current
            if str(current.phase) != "SHOP" or not current.state_complete:
                return current

            signature = joker_visual_signature(current)
            if signature != last_signature:
                last_signature = signature
                visual_stable_since = monotonic()

    def observe(self):
        previous_phase = self._last_exposed_phase
        snapshot = self._observe_public()
        phase = str(snapshot.phase)

        if snapshot.state_complete:
            if phase == "BLIND_SELECT":
                snapshot = self._wait_for_native_readiness(
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
            elif phase == "SHOP":
                snapshot = self._wait_for_native_readiness(
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

        final_phase = str(snapshot.phase)
        if (
            snapshot.state_complete
            and final_phase == "SHOP"
            and previous_phase is not None
            and _is_pack_phase(previous_phase)
        ):
            snapshot = self._wait_for_post_pack_visual_settle(snapshot)
            final_phase = str(snapshot.phase)

        self._last_exposed_phase = final_phase
        return snapshot
