import pytest

from games.balatro.live.external.shop_mouse import (
    ShopClickSequence,
    ShopMouseLayout,
    ShopPointerStep,
)
from games.balatro.live.external.shop_mouse_calibration import (
    CalibrationTarget,
    merge_capture,
    normalize_cursor,
    parse_target,
)
from games.balatro.live.external.viewport import NormalizedPoint, PixelPoint
from games.balatro.live.external.window import BalatroWindow, WindowRect


def _window():
    return BalatroWindow(
        handle=1,
        title="Balatro",
        client_rect=WindowRect(100, 200, 401, 201),
    )


def test_parse_shop_calibration_targets():
    assert parse_target("main:1:move") == CalibrationTarget(
        area="main",
        index=1,
        op="move",
    )
    assert parse_target("vouchers:0:click") == CalibrationTarget(
        area="vouchers",
        index=0,
        op="click",
    )
    assert parse_target("end_shop:click") == CalibrationTarget(
        area="end_shop",
        index=None,
        op="click",
    )


@pytest.mark.parametrize(
    "value",
    [
        "main:click",
        "main:-1:click",
        "wat:0:click",
        "main:0:drag",
    ],
)
def test_parse_shop_calibration_target_rejects_invalid_shape(value):
    with pytest.raises(ValueError):
        parse_target(value)


def test_normalize_cursor_uses_balatro_client_coordinates():
    assert normalize_cursor(
        _window(),
        PixelPoint(300, 300),
    ) == NormalizedPoint(0.5, 0.5)

    with pytest.raises(ValueError):
        normalize_cursor(_window(), PixelPoint(99, 300))


def test_merge_capture_replaces_only_targeted_shop_sequences():
    old_main = ShopClickSequence(
        (ShopPointerStep("click", NormalizedPoint(0.1, 0.1)),)
    )
    old_end = ShopClickSequence(
        (ShopPointerStep("click", NormalizedPoint(0.9, 0.9)),)
    )
    layout = ShopMouseLayout(
        main={0: old_main},
        end_shop=old_end,
    )

    new_steps = [
        ShopPointerStep("move", NormalizedPoint(0.4, 0.4)),
        ShopPointerStep("click", NormalizedPoint(0.5, 0.5)),
    ]
    merged = merge_capture(
        layout,
        {
            ("main", 1): new_steps,
        },
    )

    assert merged.main[0] == old_main
    assert merged.main[1] == ShopClickSequence(tuple(new_steps))
    assert merged.end_shop == old_end
