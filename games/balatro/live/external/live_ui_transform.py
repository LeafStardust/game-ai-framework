from __future__ import annotations

from dataclasses import dataclass

from .viewport import PixelPoint, PixelRect
from .window import WindowRect


@dataclass(frozen=True)
class BalatroLogicalViewport:
    """Map Balatro logical tile space into the current Windows client rectangle.

    Balatro's logical coordinate system is aspect-preserving. The client may be
    wider or taller than the logical canvas, so the transform uses one uniform
    scale and centers the logical canvas in the remaining letterbox space. The
    desktop origin is taken from the current client rectangle on every mapping,
    which makes window movement and monitor placement irrelevant.
    """

    logical_width: float
    logical_height: float
    client_rect: WindowRect

    def __post_init__(self) -> None:
        if self.logical_width <= 0 or self.logical_height <= 0:
            raise ValueError("Balatro logical dimensions must be positive")
        if self.client_rect.width <= 0 or self.client_rect.height <= 0:
            raise ValueError("Balatro client dimensions must be positive")

    @property
    def scale(self) -> float:
        return min(
            self.client_rect.width / self.logical_width,
            self.client_rect.height / self.logical_height,
        )

    @property
    def pad_x(self) -> float:
        return (self.client_rect.width - self.logical_width * self.scale) / 2.0

    @property
    def pad_y(self) -> float:
        return (self.client_rect.height - self.logical_height * self.scale) / 2.0

    def screen_point(self, x: float, y: float) -> PixelPoint:
        return PixelPoint(
            x=round(self.client_rect.left + self.pad_x + float(x) * self.scale),
            y=round(self.client_rect.top + self.pad_y + float(y) * self.scale),
        )

    def screen_rect(self, *, x: float, y: float, w: float, h: float) -> PixelRect:
        left = self.client_rect.left + self.pad_x + float(x) * self.scale
        top = self.client_rect.top + self.pad_y + float(y) * self.scale
        width = float(w) * self.scale
        height = float(h) * self.scale
        return PixelRect(
            left=round(left),
            top=round(top),
            width=max(1, round(width)),
            height=max(1, round(height)),
        )

    def card_center(self, geometry: dict[str, float]) -> PixelPoint:
        required = ("x", "y", "w", "h")
        missing = [name for name in required if name not in geometry]
        if missing:
            raise ValueError(
                "live Balatro card geometry is missing: " + ", ".join(missing)
            )
        return self.screen_point(
            float(geometry["x"]) + float(geometry["w"]) / 2.0,
            float(geometry["y"]) + float(geometry["h"]) / 2.0,
        )
