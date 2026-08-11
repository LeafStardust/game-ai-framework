from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
)
from games.balatro.live.shop import BalatroShopActionGenerator
from games.balatro.live.shop_sync import BufferedShopTransaction
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader
from .shop_mouse import ExternalShopMouseExecutor, ShopMouseLayout


DEFAULT_LAYOUT = "balatro-shop-mouse.json"
ACTION_NAMES = {
    "buy-joker": BUY_JOKER,
    "buy-consumable": BUY_CONSUMABLE,
    "buy-voucher": BUY_VOUCHER,
    "end-shop": END_SHOP,
}


def select_action(state, requested: str, slot: int | None):
    action_name = ACTION_NAMES[requested]
    actions = BalatroShopActionGenerator().generate_bufferable_actions(state)

    if action_name == END_SHOP:
        if slot is not None:
            raise ValueError("end-shop does not accept --slot")
        for action in actions:
            if action.name == END_SHOP:
                return action
        raise ValueError("END_SHOP is not currently available")

    if slot is None:
        raise ValueError(f"{requested} requires --slot")

    for action in actions:
        if action.name != action_name:
            continue
        if getattr(action.target, "area_index", None) == slot:
            return action

    raise ValueError(
        f"no safe affordable {requested} action exists for visible slot {slot}"
    )


def target_label(action) -> str:
    if action.name == END_SHOP:
        return "Next Round"

    target = action.target
    label = getattr(target, "label", getattr(target, "name", type(target).__name__))
    index = getattr(target, "area_index", None)
    price = getattr(target, "price", getattr(target, "cost", None))
    if isinstance(price, dict):
        price = price.get("buy")

    text = f"slot={index} {label}"
    if price is not None:
        text += f" ${price}"
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute exactly one calibrated, save-safe Balatro shop action. "
            "Mouse input is sent only when --execute is supplied."
        )
    )
    parser.add_argument("action", choices=sorted(ACTION_NAMES))
    parser.add_argument("--slot", type=int)
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument(
        "--step",
        type=int,
        help=(
            "diagnostic: execute only one 1-based calibrated pointer step; "
            "no local purchase projection is applied"
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm the mouse and send the calibrated pointer sequence",
    )
    args = parser.parse_args()

    if args.slot is not None and args.slot < 0:
        parser.error("--slot cannot be negative")
    if args.step is not None and args.step < 1:
        parser.error("--step must be at least 1")
    if args.step is not None and not args.execute:
        parser.error("--step requires --execute")

    try:
        reader = BalatroSaveReader(args.save, profile=args.profile)
        snapshot = SaveBalatroObserver(reader).observe()
        state = DefaultBalatroStateTranslator().translate(snapshot)
        if state.phase != "SHOP":
            parser.error(f"Balatro save is in {state.phase}, expected SHOP")

        layout_path = Path(args.layout)
        layout = ShopMouseLayout.load(layout_path)
        action = select_action(state, args.action, args.slot)
        sequence = layout.sequence_for(action)
        if args.step is not None and args.step > len(sequence.steps):
            parser.error(
                f"--step must be between 1 and {len(sequence.steps)} for this action"
            )
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    steps = " -> ".join(
        f"{index}:{step.op}({step.point.x:.4f},{step.point.y:.4f})"
        for index, step in enumerate(sequence.steps, start=1)
    )
    print(f"Save -> {reader.path}")
    print(f"Action -> {action.name}: {target_label(action)}")
    print(f"Sequence -> {steps}")
    print(f"Money before -> {state.money}")

    if args.step is not None:
        selected = sequence.steps[args.step - 1]
        print(
            f"Diagnostic step -> {args.step}:"
            f"{selected.op}({selected.point.x:.4f},{selected.point.y:.4f})"
        )

    if not args.execute:
        print("Mouse input sent -> False")
        print("Re-run with --execute to send exactly this one action.")
        return 0

    transaction = None
    if action.name != END_SHOP:
        transaction = BufferedShopTransaction.begin(state)

    mouse = BalatroMouseController(armed=True)
    with ExternalShopMouseExecutor(layout, mouse=mouse) as executor:
        executor.dispatch(
            action,
            state,
            transaction,
            only_step=args.step,
        )

    print("Mouse input sent -> True")
    if args.step is not None:
        print("Local purchase projection -> skipped (diagnostic single-step mode)")
        print("Inspect Balatro UI before running another diagnostic step.")
    elif transaction is not None:
        print(f"Projected money -> {state.money}")
        print(
            "Checkpoint reconciliation -> pending "
            "(save.jkr may remain stale until leaving the shop)"
        )
    else:
        print("Checkpoint reconciliation -> required after leaving shop")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
