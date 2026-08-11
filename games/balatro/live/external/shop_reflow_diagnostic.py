from __future__ import annotations

import argparse
from pathlib import Path

from .capture import save_bgra_png, save_frame_png
from .card_locator import inspect_card_face_components, locate_card_faces
from .mouse import BalatroMouseController
from .shop_mouse import ExternalShopMouseExecutor, ShopMouseLayout
from .shop_reflow import DEFAULT_SHOP_MAIN_CARD_REGION
from .viewport import BalatroViewport


DEFAULT_LAYOUT = "balatro-shop-mouse.json"
DEFAULT_FULL_OUTPUT = "balatro-shop-reflow-diagnostic-full.png"
DEFAULT_CROP_OUTPUT = "balatro-shop-reflow-diagnostic-crop.png"

# Deliberately spans the generic hand detector's normal settings down to much
# more permissive color/brightness settings. This diagnostic never clicks.
PROBES = (
    (165, 70),
    (145, 100),
    (125, 140),
    (105, 180),
)


def _normalized_component_center(region, component):
    rect = component.local_rect
    source = region.normalized_rect
    return (
        source.left + source.width * ((rect.left + rect.width / 2) / region.width),
        source.top + source.height * ((rect.top + rect.height / 2) / region.height),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture the live Balatro main-shop card region and report generic "
            "card-detector components at several threshold settings. No mouse "
            "clicks are ever sent."
        )
    )
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument("--full-output", default=DEFAULT_FULL_OUTPUT)
    parser.add_argument("--crop-output", default=DEFAULT_CROP_OUTPUT)
    args = parser.parse_args()

    try:
        layout = ShopMouseLayout.load(Path(args.layout))
        mouse = BalatroMouseController(armed=True)
        with ExternalShopMouseExecutor(layout, mouse=mouse) as executor:
            frame = executor._capture_focused_frame()
        region = BalatroViewport(frame).crop(DEFAULT_SHOP_MAIN_CARD_REGION)
        full_path = save_frame_png(frame, args.full_output)
        crop_path = save_bgra_png(
            region.width,
            region.height,
            region.bgra,
            args.crop_output,
        )
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    rect = region.pixel_rect
    nrect = region.normalized_rect
    print(
        "Shop region -> "
        f"normalized=({nrect.left:.4f},{nrect.top:.4f},"
        f"{nrect.width:.4f},{nrect.height:.4f}) "
        f"pixels=({rect.left},{rect.top},{rect.width},{rect.height})"
    )
    print(f"Full screenshot -> {full_path}")
    print(f"Shop crop -> {crop_path}")

    for brightness, spread in PROBES:
        diagnostics = inspect_card_face_components(
            region,
            min_brightness=brightness,
            max_channel_spread=spread,
        )
        locations = locate_card_faces(
            region,
            min_brightness=brightness,
            max_channel_spread=spread,
        )
        print()
        print(
            f"Probe brightness>={brightness} spread<={spread} -> "
            f"located={len(locations)} components={len(diagnostics)}"
        )
        for index, location in enumerate(locations[:8]):
            print(
                f"  L{index}: center=({location.center.x:.4f},"
                f"{location.center.y:.4f}) density={location.density:.3f}"
            )
        for index, component in enumerate(diagnostics[:12]):
            center_x, center_y = _normalized_component_center(region, component)
            rect = component.local_rect
            print(
                f"  C{index}: accepted={component.accepted} "
                f"reason={component.rejection} "
                f"center=({center_x:.4f},{center_y:.4f}) "
                f"rect=({rect.left},{rect.top},{rect.width},{rect.height}) "
                f"cells={component.cells} density={component.density:.3f}"
            )

    print()
    print("Mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
