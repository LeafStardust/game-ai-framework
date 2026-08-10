from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.actions import END_SHOP
from games.balatro.live.shop import BalatroShopActionGenerator
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader
from .shop_mouse import ShopMouseLayout, ShopMouseLayoutError


DEFAULT_LAYOUT = "balatro-shop-mouse.json"


def _target_label(action) -> str:
    if action.name == END_SHOP:
        return "Next Round"

    target = action.target
    label = getattr(target, "label", getattr(target, "name", type(target).__name__))
    index = getattr(target, "area_index", None)
    price = getattr(target, "price", getattr(target, "cost", None))
    if isinstance(price, dict):
        price = price.get("buy")

    parts = []
    if index is not None:
        parts.append(f"slot={index}")
    parts.append(str(label))
    if price is not None:
        parts.append(f"${price}")
    return " ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run current save-observed Balatro shop actions against a calibrated "
            "mouse layout. This command never sends mouse input."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    args = parser.parse_args()

    reader = BalatroSaveReader(args.save, profile=args.profile)
    snapshot = SaveBalatroObserver(reader).observe()
    state = DefaultBalatroStateTranslator().translate(snapshot)

    if state.phase != "SHOP":
        parser.error(f"Balatro save is in {state.phase}, expected SHOP")

    layout_path = Path(args.layout)
    if layout_path.exists():
        try:
            layout = ShopMouseLayout.load(layout_path)
        except (OSError, ValueError, ShopMouseLayoutError) as error:
            parser.error(str(error))
    else:
        layout = ShopMouseLayout()

    actions = BalatroShopActionGenerator().generate_bufferable_actions(state)
    missing = 0

    print(f"Save -> {reader.path}")
    print(f"Layout -> {layout_path} ({'loaded' if layout_path.exists() else 'missing'})")
    print(f"Safe shop actions -> {len(actions)}")

    for action in actions:
        try:
            sequence = layout.sequence_for(action)
        except ShopMouseLayoutError as error:
            missing += 1
            print(f"MISSING {action.name}: {_target_label(action)} -> {error}")
            continue

        steps = " -> ".join(
            f"{step.op}({step.point.x:.4f},{step.point.y:.4f})"
            for step in sequence.steps
        )
        print(f"READY   {action.name}: {_target_label(action)} -> {steps}")

    print(f"Calibration ready -> {missing == 0}")
    print("Mouse input sent -> False")
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
