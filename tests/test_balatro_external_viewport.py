import pytest

from games.balatro.live.external import (
    BalatroFrame,
    BalatroViewport,
    BalatroWindow,
    NormalizedPoint,
    NormalizedRect,
    WindowRect,
)


def _frame(width=400, height=200, bgra=None):
    if bgra is None:
        bgra = bytes(width * height * 4)
    return BalatroFrame(
        sequence=1,
        timestamp=0.0,
        window=BalatroWindow(
            handle=1,
            title="Balatro",
            client_rect=WindowRect(100, 200, width, height),
        ),
        width=width,
        height=height,
        bgra=bgra,
    )


def test_viewport_maps_normalized_points_to_frame_and_screen():
    viewport = BalatroViewport(_frame())
    point = NormalizedPoint(0.5, 0.25)

    frame_point = viewport.frame_point(point)
    screen_point = viewport.screen_point(point)

    assert frame_point.x == 200
    assert frame_point.y == 50
    assert screen_point.x == 300
    assert screen_point.y == 250


def test_viewport_maps_normalized_rectangles():
    viewport = BalatroViewport(_frame())
    rect = NormalizedRect(0.25, 0.25, 0.5, 0.5)

    frame_rect = viewport.frame_rect(rect)
    screen_rect = viewport.screen_rect(rect)

    assert (frame_rect.left, frame_rect.top) == (100, 50)
    assert (frame_rect.width, frame_rect.height) == (200, 100)
    assert (screen_rect.left, screen_rect.top) == (200, 250)
    assert (screen_rect.width, screen_rect.height) == (200, 100)


def test_viewport_crops_bgra_region_without_resizing():
    pixels = []
    for value in range(8):
        pixels.extend((value, 0, 0, 255))

    viewport = BalatroViewport(_frame(4, 2, bytes(pixels)))
    region = viewport.crop(NormalizedRect(0.5, 0.0, 0.5, 1.0))

    assert (region.width, region.height) == (2, 2)
    assert list(region.bgra[0::4]) == [2, 3, 6, 7]


def test_normalized_coordinates_reject_out_of_bounds_values():
    with pytest.raises(ValueError):
        NormalizedPoint(1.1, 0.5)

    with pytest.raises(ValueError):
        NormalizedRect(0.75, 0.0, 0.5, 1.0)
