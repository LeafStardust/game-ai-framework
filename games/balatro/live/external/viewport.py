from __future__ import annotations

import math
from dataclasses import dataclass

from .capture import BalatroFrame


@dataclass(frozen=True)
class NormalizedPoint:
    x: float
    y: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.x <= 1.0 or not 0.0 <= self.y <= 1.0:
            raise ValueError("normalized point coordinates must be between 0 and 1")


@dataclass(frozen=True)
class NormalizedRect:
    left: float
    top: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.left < 0.0 or self.top < 0.0:
            raise ValueError("normalized rectangle origin cannot be negative")
        if self.width <= 0.0 or self.height <= 0.0:
            raise ValueError("normalized rectangle size must be positive")
        if self.right > 1.0 or self.bottom > 1.0:
            raise ValueError("normalized rectangle must fit inside the viewport")

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height

    @property
    def center(self) -> NormalizedPoint:
        return NormalizedPoint(
            self.left + self.width / 2.0,
            self.top + self.height / 2.0,
        )


@dataclass(frozen=True)
class PixelPoint:
    x: int
    y: int


@dataclass(frozen=True)
class PixelRect:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def center(self) -> PixelPoint:
        return PixelPoint(
            self.left + self.width // 2,
            self.top + self.height // 2,
        )


@dataclass(frozen=True)
class FrameRegion:
    normalized_rect: NormalizedRect
    pixel_rect: PixelRect
    width: int
    height: int
    bgra: bytes


class BalatroViewport:
    """Maps resolution-independent Balatro coordinates to a captured client area."""

    def __init__(self, frame: BalatroFrame):
        if frame.width <= 0 or frame.height <= 0:
            raise ValueError("Balatro frame dimensions must be positive")
        self.frame = frame

    def frame_point(self, point: NormalizedPoint) -> PixelPoint:
        return PixelPoint(
            self._point_axis(point.x, self.frame.width),
            self._point_axis(point.y, self.frame.height),
        )

    def screen_point(self, point: NormalizedPoint) -> PixelPoint:
        frame_point = self.frame_point(point)
        rect = self.frame.window.client_rect
        return PixelPoint(
            rect.left + frame_point.x,
            rect.top + frame_point.y,
        )

    def frame_rect(self, rect: NormalizedRect) -> PixelRect:
        left = math.floor(rect.left * self.frame.width)
        top = math.floor(rect.top * self.frame.height)
        right = math.ceil(rect.right * self.frame.width)
        bottom = math.ceil(rect.bottom * self.frame.height)

        left = min(max(left, 0), self.frame.width - 1)
        top = min(max(top, 0), self.frame.height - 1)
        right = min(max(right, left + 1), self.frame.width)
        bottom = min(max(bottom, top + 1), self.frame.height)

        return PixelRect(
            left=left,
            top=top,
            width=right - left,
            height=bottom - top,
        )

    def screen_rect(self, rect: NormalizedRect) -> PixelRect:
        frame_rect = self.frame_rect(rect)
        window_rect = self.frame.window.client_rect
        return PixelRect(
            left=window_rect.left + frame_rect.left,
            top=window_rect.top + frame_rect.top,
            width=frame_rect.width,
            height=frame_rect.height,
        )

    def crop(self, rect: NormalizedRect) -> FrameRegion:
        pixel_rect = self.frame_rect(rect)
        stride = self.frame.width * 4
        row_size = pixel_rect.width * 4
        rows = []

        for y in range(pixel_rect.top, pixel_rect.bottom):
            start = y * stride + pixel_rect.left * 4
            rows.append(self.frame.bgra[start : start + row_size])

        return FrameRegion(
            normalized_rect=rect,
            pixel_rect=pixel_rect,
            width=pixel_rect.width,
            height=pixel_rect.height,
            bgra=b"".join(rows),
        )

    @staticmethod
    def _point_axis(value: float, size: int) -> int:
        if size <= 1:
            return 0
        return min(size - 1, max(0, round(value * (size - 1))))
