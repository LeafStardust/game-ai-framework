from __future__ import annotations

import time

from .capture import BalatroScreenCapture
from .consumable_mouse import ConsumableMouseLayout, ConsumableMouseLayoutError
from .expected_card_locator import locate_card_faces_expected_count
from .hand_mouse import ExternalHandMouseExecutor, HandMouseLayout
from .mouse import BalatroMouseController
from .viewport import BalatroViewport


class ExternalJudgementMouseExecutor:
    """Execute exactly one Judgement use through normal mouse input.

    Judgement has no card target. The executor still validates the full visible hand
    against the save-backed card count before clicking the held consumable so an
    unexpected UI state cannot silently shift the calibrated controls.
    """

    def __init__(
        self,
        layout: ConsumableMouseLayout,
        capture: BalatroScreenCapture | None = None,
        mouse: BalatroMouseController | None = None,
        *,
        before_consumable_delay: float = 0.20,
        before_use_delay: float = 0.25,
    ):
        self.layout = layout
        self.capture = capture or BalatroScreenCapture()
        self.mouse = mouse or BalatroMouseController()
        self.before_consumable_delay = max(0.0, float(before_consumable_delay))
        self.before_use_delay = max(0.0, float(before_use_delay))

    def dispatch(self, state, consumable) -> int:
        self._validate(state, consumable)
        expected_count = len(state.hand)
        locator = lambda region: locate_card_faces_expected_count(region, expected_count)

        hand_executor = ExternalHandMouseExecutor(
            HandMouseLayout(),
            capture=self.capture,
            mouse=self.mouse,
            card_locator=locator,
        )
        frame, locations = hand_executor.locate_hand(state)
        if len(locations) != expected_count:
            raise ConsumableMouseLayoutError(
                "Judgement screen/save exact-count guard failed"
            )

        viewport = BalatroViewport(frame)
        area_index = int(getattr(consumable, "area_index"))

        if self.before_consumable_delay > 0:
            time.sleep(self.before_consumable_delay)
        self.mouse.click_screen(
            viewport.screen_point(self.layout.point_for_slot(area_index))
        )

        if self.before_use_delay > 0:
            time.sleep(self.before_use_delay)
        self.mouse.click_screen(
            viewport.screen_point(self.layout.use_point_for_slot(area_index))
        )
        return area_index

    @staticmethod
    def _validate(state, consumable) -> None:
        if getattr(state, "phase", None) != "SELECTING_HAND":
            raise ConsumableMouseLayoutError(
                "Judgement external executor requires SELECTING_HAND"
            )
        if getattr(consumable, "name", None) != "Judgement":
            raise ConsumableMouseLayoutError(
                "Judgement executor received a different consumable"
            )
        if consumable not in getattr(state, "consumables", ()):
            raise ConsumableMouseLayoutError(
                "Judgement is not present in the authoritative consumable list"
            )
        area_index = getattr(consumable, "area_index", None)
        if not isinstance(area_index, int) or isinstance(area_index, bool):
            raise ConsumableMouseLayoutError(
                "Judgement save observation has no authoritative area_index"
            )
        if area_index not in {0, 1}:
            raise ConsumableMouseLayoutError(
                f"unsupported Judgement held area_index: {area_index}"
            )
        if getattr(consumable, "live_id", None) is None:
            raise ConsumableMouseLayoutError("Judgement has no stable live_id")
        if len(getattr(state, "jokers", ())) >= int(getattr(state, "joker_slots", 5)):
            raise ConsumableMouseLayoutError("no Joker slot is available for Judgement")

    def close(self) -> None:
        self.capture.close()

    def __enter__(self) -> "ExternalJudgementMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
