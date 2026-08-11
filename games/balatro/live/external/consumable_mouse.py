from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .capture import BalatroScreenCapture
from .expected_card_locator import locate_card_faces_expected_count
from .hand_mouse import ExternalHandMouseExecutor, HandMouseLayout
from .mouse import BalatroMouseController
from .viewport import BalatroViewport, NormalizedPoint


class ConsumableMouseLayoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConsumableMouseLayout:
    """Resolution-independent held-consumable slots and slot-specific Use buttons."""

    slot_0: NormalizedPoint | None = None
    slot_1: NormalizedPoint | None = None
    use_0: NormalizedPoint | None = None
    use_1: NormalizedPoint | None = None

    def point_for_slot(self, index: int) -> NormalizedPoint:
        if index == 0:
            point = self.slot_0
        elif index == 1:
            point = self.slot_1
        else:
            raise ConsumableMouseLayoutError(
                f"unsupported held consumable area index: {index}"
            )
        if point is None:
            raise ConsumableMouseLayoutError(
                f"held consumable slot {index} is not calibrated"
            )
        return point

    def use_point_for_slot(self, index: int) -> NormalizedPoint:
        if index == 0:
            point = self.use_0
        elif index == 1:
            point = self.use_1
        else:
            raise ConsumableMouseLayoutError(
                f"unsupported held consumable area index: {index}"
            )
        if point is None:
            raise ConsumableMouseLayoutError(
                f"consumable Use button for slot {index} is not calibrated"
            )
        return point

    @classmethod
    def load(cls, path: str | Path) -> "ConsumableMouseLayout":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ConsumableMouseLayoutError(
                "consumable mouse layout must be a JSON object"
            )
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "ConsumableMouseLayout":
        return cls(
            slot_0=cls._point_from_value(raw.get("slot_0")),
            slot_1=cls._point_from_value(raw.get("slot_1")),
            use_0=cls._point_from_value(raw.get("use_0")),
            use_1=cls._point_from_value(raw.get("use_1")),
        )

    def to_dict(self) -> dict:
        return {
            "slot_0": self._point_to_value(self.slot_0),
            "slot_1": self._point_to_value(self.slot_1),
            "use_0": self._point_to_value(self.use_0),
            "use_1": self._point_to_value(self.use_1),
        }

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output

    @staticmethod
    def _point_from_value(value) -> NormalizedPoint | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ConsumableMouseLayoutError(
                "consumable mouse target must be an object"
            )
        try:
            return NormalizedPoint(float(value["x"]), float(value["y"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ConsumableMouseLayoutError(
                f"invalid consumable mouse target: {value!r}"
            ) from error

    @staticmethod
    def _point_to_value(point: NormalizedPoint | None):
        if point is None:
            return None
        return {"x": point.x, "y": point.y}


class ExternalSunMouseExecutor:
    """Execute exactly one validated The Sun use through normal mouse input."""

    def __init__(
        self,
        layout: ConsumableMouseLayout,
        capture: BalatroScreenCapture | None = None,
        mouse: BalatroMouseController | None = None,
        *,
        between_card_delay: float = 0.12,
        before_consumable_delay: float = 0.20,
        before_use_delay: float = 0.25,
    ):
        self.layout = layout
        self.capture = capture or BalatroScreenCapture()
        self.mouse = mouse or BalatroMouseController()
        self.between_card_delay = max(0.0, float(between_card_delay))
        self.before_consumable_delay = max(0.0, float(before_consumable_delay))
        self.before_use_delay = max(0.0, float(before_use_delay))

    def dispatch(
        self,
        state,
        consumable,
        target_indices: tuple[int, ...],
    ) -> tuple[int, ...]:
        self._validate(state, consumable, target_indices)
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
                "The Sun screen/save exact-count guard failed"
            )

        viewport = BalatroViewport(frame)
        for offset, index in enumerate(target_indices):
            self.mouse.click_screen(viewport.screen_point(locations[index].center))
            if offset + 1 < len(target_indices) and self.between_card_delay > 0:
                time.sleep(self.between_card_delay)

        if self.before_consumable_delay > 0:
            time.sleep(self.before_consumable_delay)

        area_index = int(getattr(consumable, "area_index"))
        self.mouse.click_screen(
            viewport.screen_point(self.layout.point_for_slot(area_index))
        )

        if self.before_use_delay > 0:
            time.sleep(self.before_use_delay)

        self.mouse.click_screen(
            viewport.screen_point(self.layout.use_point_for_slot(area_index))
        )
        return target_indices

    @staticmethod
    def _validate(state, consumable, target_indices: tuple[int, ...]) -> None:
        if getattr(state, "phase", None) != "SELECTING_HAND":
            raise ConsumableMouseLayoutError(
                "The Sun external executor requires SELECTING_HAND"
            )
        if getattr(consumable, "name", None) != "The Sun":
            raise ConsumableMouseLayoutError(
                "external consumable executor currently supports only The Sun"
            )
        if consumable not in getattr(state, "consumables", ()):
            raise ConsumableMouseLayoutError(
                "The Sun target is not present in the authoritative consumable list"
            )
        area_index = getattr(consumable, "area_index", None)
        if not isinstance(area_index, int) or isinstance(area_index, bool):
            raise ConsumableMouseLayoutError(
                "The Sun save observation has no authoritative area_index"
            )
        if area_index not in {0, 1}:
            raise ConsumableMouseLayoutError(
                f"unsupported The Sun held area_index: {area_index}"
            )
        if not 1 <= len(target_indices) <= 3:
            raise ConsumableMouseLayoutError(
                "The Sun must target between one and three hand cards"
            )
        if len(set(target_indices)) != len(target_indices):
            raise ConsumableMouseLayoutError("The Sun target indices must be unique")
        if any(index < 0 or index >= len(state.hand) for index in target_indices):
            raise ConsumableMouseLayoutError("The Sun target index is out of range")
        for index in target_indices:
            card = state.hand[index]
            if getattr(card, "live_id", None) is None:
                raise ConsumableMouseLayoutError(
                    "The Sun target card is missing a stable live_id"
                )

    def close(self) -> None:
        self.capture.close()

    def __enter__(self) -> "ExternalSunMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
