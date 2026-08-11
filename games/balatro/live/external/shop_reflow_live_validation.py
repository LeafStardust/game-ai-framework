from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.actions import BUY_CONSUMABLE, BUY_JOKER, END_SHOP
from games.balatro.live.shop import BalatroShopActionGenerator
from games.balatro.live.shop_sync import BufferedShopTransaction
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader
from .shop_mouse import ExternalShopMouseExecutor, ShopMouseLayout
from .shop_reflow import ShopMainReflowLocator
from .viewport import BalatroViewport


DEFAULT_LAYOUT = "balatro-shop-mouse.json"
MAIN_PURCHASES = {BUY_JOKER, BUY_CONSUMABLE}


def _label(action) -> str:
    if action.name == END_SHOP:
        return "Next Round"
    target = action.target
    return str(getattr(target, "label", getattr(target, "name", type(target).__name__)))


def _find_main_purchase(state, label: str):
    actions = BalatroShopActionGenerator().generate_bufferable_actions(state)
    matches = [
        action
        for action in actions
        if action.name in MAIN_PURCHASES and _label(action) == label
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one visible main-shop item labelled {label!r}, "
            f"found {len(matches)}"
        )
    return matches[0]


def _sequence_text(sequence) -> str:
    return " -> ".join(
        f"{index}:{step.op}({step.point.x:.4f},{step.point.y:.4f})"
        for index, step in enumerate(sequence.steps, start=1)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct one already-buffered main-shop purchase from a stale save, "
            "then locate a remaining shop card from fresh screen geometry."
        )
    )
    parser.add_argument("--purchased-label", required=True)
    parser.add_argument("--expect-label", required=True)
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--hover-only",
        action="store_true",
        help="move the cursor to the freshly detected card without clicking",
    )
    mode.add_argument(
        "--execute-card-click",
        action="store_true",
        help=(
            "after all guards pass, click only the freshly detected card position; "
            "the Buy button is never clicked by this diagnostic"
        ),
    )
    args = parser.parse_args()

    try:
        reader = BalatroSaveReader(args.save, profile=args.profile)
        observer = SaveBalatroObserver(reader)
        state = DefaultBalatroStateTranslator().translate(observer.observe())
        if state.phase != "SHOP":
            parser.error(f"Balatro save is in {state.phase}, expected SHOP")

        transaction = BufferedShopTransaction.begin(state)
        purchased = _find_main_purchase(state, args.purchased_label)
        transaction.apply(state, purchased)
        expected = _find_main_purchase(state, args.expect_label)

        layout = ShopMouseLayout.load(Path(args.layout))
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(f"Save -> {reader.path}")
    print(f"Stale save money -> {transaction.baseline_money}")
    print(
        f"Reconstructed purchase -> {purchased.name}: {args.purchased_label}"
    )
    print(f"Projected money -> {state.money}")
    print(f"Expected remaining target -> {expected.name}: {args.expect_label}")

    mouse = BalatroMouseController(armed=True)
    try:
        with ExternalShopMouseExecutor(layout, mouse=mouse) as executor:
            locator = ShopMainReflowLocator(executor)
            target = locator.locate(state, expected)

            print(f"Fresh visible main cards -> {target.visible_count}")
            print(f"Mapped visible index -> {target.visible_index}")
            print(
                "Detected target center -> "
                f"({target.card.center.x:.4f},{target.card.center.y:.4f})"
            )
            print(f"Dynamic sequence -> {_sequence_text(target.sequence)}")

            if args.hover_only:
                frame = executor._capture_focused_frame()
                point = BalatroViewport(frame).screen_point(target.sequence.steps[0].point)
                mouse.move_screen(point)
                print("Mouse input sent -> True (move only)")
                print("Clicked -> False")
                print(f"Expected cursor target -> {args.expect_label}")
                return 0

            if not args.execute_card_click:
                print("Mouse input sent -> False")
                print(
                    "Re-run with --hover-only to move the cursor onto the detected "
                    "card without clicking."
                )
                return 0

            locator.dispatch(
                expected,
                state,
                transaction,
                only_step=1,
            )
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print("Mouse input sent -> True")
    print("Dynamic purchase step -> card click only")
    print("Buy button clicked -> False")
    print("Local second-purchase projection -> False")
    print(f"Expected selected card -> {args.expect_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
