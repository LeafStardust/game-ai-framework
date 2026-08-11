from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.actions import END_SHOP
from games.balatro.live.shop import BalatroShopActionGenerator
from games.balatro.live.shop_sync import BufferedShopTransaction
from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader
from .shop_mouse import ExternalShopMouseExecutor, ShopMouseLayout


DEFAULT_LAYOUT = "balatro-shop-mouse.json"


def _label(item) -> str:
    return str(getattr(item, "label", getattr(item, "name", type(item).__name__)))


def _find_purchase(state, label: str):
    actions = BalatroShopActionGenerator().generate_bufferable_actions(state)
    matches = [
        action
        for action in actions
        if action.name != END_SHOP and _label(action.target) == label
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one buffer-safe shop item labelled {label!r}, "
            f"found {len(matches)}"
        )
    return matches[0]


def _owned_labels(state) -> set[str]:
    return {
        _label(item)
        for item in [*state.jokers, *state.consumables, *state.vouchers]
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct already-executed buffered shop purchases from the stale "
            "SHOP save, click Next Round exactly once, and verify the persisted "
            "checkpoint acknowledges their money and owned-item effects."
        )
    )
    parser.add_argument(
        "--purchased-label",
        action="append",
        required=True,
        help="visible label of an already-executed buffered purchase; repeat in purchase order",
    )
    parser.add_argument("--expect-money", type=int, required=True)
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm mouse input, click Next Round once, and wait for BLIND_SELECT",
    )
    args = parser.parse_args()

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()

    try:
        snapshot = observer.observe()
        state = translator.translate(snapshot)
        if state.phase != "SHOP":
            parser.error(f"Balatro save is in {state.phase}, expected SHOP")

        transaction = BufferedShopTransaction.begin(state)
        reconstructed = []
        for label in args.purchased_label:
            action = _find_purchase(state, label)
            transaction.apply(state, action)
            reconstructed.append(action)

        if state.money != args.expect_money:
            parser.error(
                "reconstructed money mismatch: "
                f"expected={args.expect_money}, projected={state.money}"
            )

        end_shop = next(
            action
            for action in BalatroShopActionGenerator().generate_bufferable_actions(state)
            if action.name == END_SHOP
        )
        layout = ShopMouseLayout.load(Path(args.layout))
    except (OSError, RuntimeError, StopIteration, ValueError) as error:
        parser.error(str(error))

    print(f"Save -> {reader.path}")
    print(f"Stale save money -> {transaction.baseline_money}")
    for index, action in enumerate(reconstructed, start=1):
        print(f"Reconstructed purchase {index} -> {action.name}: {_label(action.target)}")
    print(f"Projected money -> {state.money}")
    print(f"Expected checkpoint money -> {args.expect_money}")
    print("Control -> Next Round")

    if not args.execute:
        print("Mouse input sent -> False")
        print("Re-run with --execute to leave the shop and verify the checkpoint.")
        return 0

    mouse = BalatroMouseController(armed=True)
    try:
        with ExternalShopMouseExecutor(layout, mouse=mouse) as executor:
            executor.dispatch(end_shop, state)

        print("Mouse input sent -> True")
        print("Waiting for save checkpoint -> BLIND_SELECT")
        persisted_snapshot = BalatroLiveSynchronizer(
            observer,
            poll_interval=0.05,
            timeout=15.0,
        ).wait_for_change(
            snapshot,
            phases={"BLIND_SELECT"},
            require_complete=False,
        )
        persisted_state = translator.translate(persisted_snapshot)
        transaction.assert_reconciled(persisted_state)

        labels = _owned_labels(persisted_state)
        missing = [label for label in args.purchased_label if label not in labels]
        if missing:
            raise RuntimeError(
                "persisted checkpoint is missing reconstructed purchased item(s): "
                + ", ".join(missing)
            )
    except (OSError, RuntimeError, TimeoutError, ValueError) as error:
        parser.error(str(error))

    print("Checkpoint reconciliation -> PASS")
    print(f"Persisted phase -> {persisted_state.phase}")
    print(f"Persisted money -> {persisted_state.money}")
    print("Persisted purchased labels -> " + ", ".join(args.purchased_label))
    print("Buffered multi-buy checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
