from games.balatro.live.external.live_ui_transform import BalatroLogicalViewport
from games.balatro.live.external.window import WindowRect


def test_transform_uses_uniform_scale_and_centered_letterbox():
    transform = BalatroLogicalViewport(
        20.0,
        11.5,
        WindowRect(left=-1736, top=165, width=1536, height=864),
    )

    assert round(transform.scale, 6) == round(864 / 11.5, 6)
    assert round(transform.pad_x, 6) == round((1536 - 20 * transform.scale) / 2, 6)
    assert abs(transform.pad_y) < 1e-9

    center = transform.card_center(
        {"x": 4.836622, "y": 6.936311, "w": 2.048780, "h": 2.751220}
    )
    assert center.x == -1279
    assert center.y == 790


def test_window_movement_changes_only_desktop_offset():
    geometry = {"x": 10.0, "y": 5.0, "w": 2.0, "h": 3.0}
    first = BalatroLogicalViewport(
        20.0,
        11.5,
        WindowRect(left=100, top=200, width=1536, height=864),
    ).card_center(geometry)
    moved = BalatroLogicalViewport(
        20.0,
        11.5,
        WindowRect(left=460, top=-40, width=1536, height=864),
    ).card_center(geometry)

    assert moved.x - first.x == 360
    assert moved.y - first.y == -240


def test_resize_or_fullscreen_recomputes_scale_from_current_client_rect():
    geometry = {"x": 9.0, "y": 5.0, "w": 2.0, "h": 2.0}
    windowed = BalatroLogicalViewport(
        20.0,
        11.5,
        WindowRect(left=20, top=30, width=1280, height=720),
    )
    fullscreen = BalatroLogicalViewport(
        20.0,
        11.5,
        WindowRect(left=0, top=0, width=1920, height=1080),
    )

    assert windowed.scale != fullscreen.scale
    assert windowed.card_center(geometry) != fullscreen.card_center(geometry)


def test_tall_client_letterboxes_vertically():
    transform = BalatroLogicalViewport(
        20.0,
        11.5,
        WindowRect(left=0, top=0, width=1200, height=900),
    )

    assert transform.scale == 60.0
    assert transform.pad_x == 0.0
    assert transform.pad_y == 105.0
