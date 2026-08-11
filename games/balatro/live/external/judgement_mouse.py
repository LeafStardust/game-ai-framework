from __future__ import annotations

import time

from .capture import BalatroFrame, BalatroScreenCapture
from .consumable_mouse import ConsumableMouseLayout, ConsumableMouseLayoutError
from .expected_card_locator import locate_card_faces_expected_count
from .hand_mouse import ExternalHandMouseExecutor, HandMouseLayout
from .mouse import BalatroMouseController
from .viewport import BalatroViewport, NormalizedPoint


class ExternalJudgementMouseExecutor:
    """Execute exactly one Judgement use through normal mouse input.

    Judgement has no card target. The executor validates the full visible hand
    against the save-backed card count, opens the authoritative held-consumable
    slot, then requires a visible UI change around that slot's calibrated Use
    control before the destructive Use click is allowed.
    """

    USE_PATCH_HALF_WIDTH = 0.055
    USE_PATCH_HALF_HEIGHT = 0.040
    USE_CHANGED_CHANNEL_DELTA = 20
    USE_CHANGED_PIXEL_RATIO = 0.04

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
        slot_point = self.layout.point_for_slot(area_index)
        use_point = self.layout.use_point_for_slot(area_index)

        if self.before_consumable_delay > 0:
            time.sleep(self.before_consumable_delay)
        self.mouse.click_screen(viewport.screen_point(slot_point))

        if self.before_use_delay > 0:
            time.sleep(self.before_use_delay)

        opened_frame = self.capture.capture()
        if not self.use_control_changed(frame, opened_frame, use_point):
            raise ConsumableMouseLayoutError(
                "Judgement slot click did not expose the calibrated Use control; "
                "no Use click was sent. Recalibrate slot/use coordinates or inspect "
                "the consumable UI state."
            )

        opened_viewport = BalatroViewport(opened_frame)
        self.mouse.click_screen(opened_viewport.screen_point(use_point))
        return area_index

    @classmethod
    def use_control_changed(
        cls,
        before: BalatroFrame,
        after: BalatroFrame,
        point: NormalizedPoint,
    ) -> bool:
        if before.width != after.width or before.height != after.height:
            return False
        if len(before.bgra) != len(after.bgra):
            return False

        width = before.width
        height = before.height
        center_x = round(point.x * width)
        center_y = round(point.y * height)
        half_width = max(2, round(cls.USE_PATCH_HALF_WIDTH * width))
        half_height = max(2, round(cls.USE_PATCH_HALF_HEIGHT * height))
        x0 = max(0, center_x - half_width)
        x1 = min(width, center_x + half_width + 1)
        y0 = max(0, center_y - half_height)
        y1 = min(height, center_y + half_height + 1)
        if x0 >= x1 or y0 >= y1:
            return False

        changed = 0
        total = 0
        stride = width * 4
        threshold = cls.USE_CHANGED_CHANNEL_DELTA
        for y in range(y0, y1):
            row = y * stride
            for x in range(x0, x1):
                offset = row + x * 4
                before_pixel = before.bgra[offset : offset + 3]
                after_pixel = after.bgra[offset : offset + 3]
                if len(before_pixel) < 3 or len(after_pixel) < 3:
                    return False
                if max(
                    abs(int(before_pixel[channel]) - int(after_pixel[channel]))
                    for channel in range(3)
                ) >= threshold:
                    changed += 1
                total += 1

        return total > 0 and changed / total >= cls.USE_CHANGED_PIXEL_RATIO

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
