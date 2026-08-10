from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    REFRESH_SHOP,
)
from games.balatro.actions import BalatroAction
from games.balatro.live.shop_sync import (
    BufferedShopTransaction,
    UnsupportedBufferedShopAction,
)
from games.balatro.state import BalatroState

from .capture import BalatroFrame, BalatroScreenCapture
from .mouse import BalatroMouseController
from .viewport import BalatroViewport, NormalizedPoint


class ShopMouseLayoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class ShopPointerStep:
    op: str
    point: NormalizedPoint
    delay: float = 0.0

    def __post_init__(self) -> None:
        if self.op not in {"move", "click"}:
            raise ValueError("shop pointer step op must be 'move' or 'click'")
        if self.delay < 0:
            raise ValueError("shop pointer step delay cannot be negative")


@dataclass(frozen=True)
class ShopClickSequence:
    steps: tuple[ShopPointerStep, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("shop click sequence requires at least one pointer step")


@dataclass(frozen=True)
class ShopMouseLayout:
    """Resolution-independent calibrated pointer sequences for Balatro shop controls."""

    main: dict[int, ShopClickSequence] = field(default_factory=dict)
    boosters: dict[int, ShopClickSequence] = field(default_factory=dict)
    vouchers: dict[int, ShopClickSequence] = field(default_factory=dict)
    end_shop: ShopClickSequence | None = None
    reroll: ShopClickSequence | None = None

    def sequence_for(self, action: BalatroAction) -> ShopClickSequence:
        if action.name == END_SHOP:
            if self.end_shop is None:
                raise ShopMouseLayoutError("END_SHOP is not calibrated")
            return self.end_shop

        if action.name == REFRESH_SHOP:
            if self.reroll is None:
                raise ShopMouseLayoutError("REFRESH_SHOP is not calibrated")
            return self.reroll

        target = action.target
        area_index = getattr(target, "area_index", None)
        if area_index is None:
            raise ShopMouseLayoutError(
                f"{action.name} target has no observable shop area_index"
            )
        try:
            area_index = int(area_index)
        except (TypeError, ValueError) as error:
            raise ShopMouseLayoutError(
                f"invalid shop area_index: {area_index!r}"
            ) from error

        if action.name in {BUY_JOKER, BUY_CONSUMABLE}:
            sequences = self.main
            area_name = "main"
        elif action.name == BUY_BOOSTER:
            sequences = self.boosters
            area_name = "boosters"
        elif action.name == BUY_VOUCHER:
            sequences = self.vouchers
            area_name = "vouchers"
        else:
            raise ShopMouseLayoutError(
                f"unsupported shop mouse action: {action.name}"
            )

        sequence = sequences.get(area_index)
        if sequence is None:
            raise ShopMouseLayoutError(
                f"shop {area_name} slot {area_index} is not calibrated"
            )
        return sequence

    @classmethod
    def load(cls, path: str | Path) -> "ShopMouseLayout":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ShopMouseLayoutError("shop mouse layout must be a JSON object")
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "ShopMouseLayout":
        return cls(
            main=cls._area_from_dict(raw.get("main")),
            boosters=cls._area_from_dict(raw.get("boosters")),
            vouchers=cls._area_from_dict(raw.get("vouchers")),
            end_shop=cls._sequence_from_value(raw.get("end_shop")),
            reroll=cls._sequence_from_value(raw.get("reroll")),
        )

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output

    def to_dict(self) -> dict:
        return {
            "main": self._area_to_dict(self.main),
            "boosters": self._area_to_dict(self.boosters),
            "vouchers": self._area_to_dict(self.vouchers),
            "end_shop": self._sequence_to_value(self.end_shop),
            "reroll": self._sequence_to_value(self.reroll),
        }

    @classmethod
    def _area_from_dict(cls, value) -> dict[int, ShopClickSequence]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ShopMouseLayoutError("shop mouse area calibration must be an object")

        result = {}
        for key, sequence in value.items():
            try:
                index = int(key)
            except (TypeError, ValueError) as error:
                raise ShopMouseLayoutError(
                    f"shop mouse slot key must be an integer: {key!r}"
                ) from error
            parsed = cls._sequence_from_value(sequence)
            if parsed is None:
                raise ShopMouseLayoutError(
                    f"shop mouse slot {index} has an empty sequence"
                )
            result[index] = parsed
        return result

    @classmethod
    def _sequence_from_value(cls, value) -> ShopClickSequence | None:
        if value is None:
            return None
        if not isinstance(value, list) or not value:
            raise ShopMouseLayoutError("shop mouse sequence must be a non-empty list")

        steps = []
        for raw_step in value:
            if not isinstance(raw_step, dict):
                raise ShopMouseLayoutError("shop mouse pointer step must be an object")
            try:
                point = NormalizedPoint(
                    float(raw_step["x"]),
                    float(raw_step["y"]),
                )
                step = ShopPointerStep(
                    op=str(raw_step.get("op", "click")).lower(),
                    point=point,
                    delay=float(raw_step.get("delay", 0.0)),
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ShopMouseLayoutError(
                    f"invalid shop mouse pointer step: {raw_step!r}"
                ) from error
            steps.append(step)
        return ShopClickSequence(tuple(steps))

    @staticmethod
    def _area_to_dict(area: dict[int, ShopClickSequence]) -> dict[str, list[dict]]:
        return {
            str(index): ShopMouseLayout._sequence_to_value(sequence)
            for index, sequence in sorted(area.items())
        }

    @staticmethod
    def _sequence_to_value(sequence: ShopClickSequence | None):
        if sequence is None:
            return None
        return [
            {
                "op": step.op,
                "x": step.point.x,
                "y": step.point.y,
                "delay": step.delay,
            }
            for step in sequence.steps
        ]


class ExternalShopMouseExecutor:
    """Dispatch calibrated shop pointer input and project deterministic purchases locally."""

    BUFFERED_PURCHASES = {
        BUY_JOKER,
        BUY_CONSUMABLE,
        BUY_VOUCHER,
    }

    def __init__(
        self,
        layout: ShopMouseLayout,
        capture: BalatroScreenCapture | None = None,
        mouse: BalatroMouseController | None = None,
    ):
        self.layout = layout
        self.capture = capture or BalatroScreenCapture()
        self.mouse = mouse or BalatroMouseController()

    def dispatch(
        self,
        action: BalatroAction,
        state: BalatroState,
        transaction: BufferedShopTransaction | None = None,
    ) -> BalatroFrame:
        if state.phase != "SHOP":
            raise ValueError("external shop mouse actions require SHOP phase")

        if action.name in {BUY_BOOSTER, REFRESH_SHOP}:
            raise UnsupportedBufferedShopAction(
                f"shop action {action.name!r} requires immediate post-action observation"
            )

        if action.name in self.BUFFERED_PURCHASES:
            if transaction is None:
                raise ValueError(
                    "deterministic shop purchases require a BufferedShopTransaction"
                )
            transaction.validate(state, action)

        sequence = self.layout.sequence_for(action)
        frame = self.capture.capture()
        viewport = BalatroViewport(frame)
        self.mouse.focus(frame.window)

        for step in sequence.steps:
            screen_point = viewport.screen_point(step.point)
            if step.op == "move":
                self.mouse.move_screen(screen_point)
            else:
                self.mouse.click_screen(screen_point)
            if step.delay > 0:
                time.sleep(step.delay)

        if action.name in self.BUFFERED_PURCHASES:
            transaction.apply(state, action)

        return frame

    def close(self) -> None:
        self.capture.close()

    def __enter__(self) -> "ExternalShopMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
