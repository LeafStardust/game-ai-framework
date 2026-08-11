from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.actions import END_SHOP
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.shop_policy import BalatroShopPolicy

from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader
from .shop_controller import ExternalShopController
from .shop_mouse import ExternalShopMouseExecutor, ShopMouseLayout


DEFAULT_LAYOUT = "balatro-shop-mouse.json"


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


def item_label(action) -> str:
    if action.name == END_SHOP:
        return "Next Round"
    target = action.target
    return str(getattr(target, "label", getattr(target, "name", type(target).__name__)))


def print_ranking(ranked, *, heading: str) -> None:
    print(heading)
    for index, result in enumerate(ranked, start=1):
        action = result.action
        print(
            f"{index}. {action.name}: {target_label(action)} "
            f"score={result.total:.3f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute exactly one policy-recommended, buffer-safe Balatro "
            "shop purchase. With --finish-if-done, execution may also leave the shop "
            "when the projected re-rank recommends END_SHOP."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm mouse input and execute exactly one recommended purchase",
    )
    parser.add_argument(
        "--expect-label",
        help=(
            "required with --execute; exact visible item label expected to be the "
            "current recommendation"
        ),
    )
    parser.add_argument(
        "--finish-if-done",
        action="store_true",
        help=(
            "after the one purchase, leave the shop and reconcile the checkpoint "
            "only if the projected next recommendation is END_SHOP"
        ),
    )
    args = parser.parse_args()

    if args.execute and not args.expect_label:
        parser.error("--execute requires --expect-label")
    if args.expect_label and not args.execute:
        parser.error("--expect-label is only valid with --execute")
    if args.finish_if_done and not args.execute:
        parser.error("--finish-if-done requires --execute")

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()
    policy = BalatroShopPolicy()

    if not args.execute:
        snapshot = observer.observe()
        state = translator.translate(snapshot)
        if state.phase != "SHOP":
            parser.error(f"Balatro save is in {state.phase}, expected SHOP")

        from games.balatro.live.shop import BalatroShopActionGenerator

        actions = BalatroShopActionGenerator().generate_bufferable_actions(state)
        ranked = policy.rank_actions(state, actions)

        print(f"Save -> {reader.path}")
        print(f"Money -> {state.money}")
        print_ranking(ranked, heading="Current ranking:")
        if ranked:
            best = ranked[0].action
            print(f"Recommended -> {best.name}: {target_label(best)}")
        else:
            print("Recommended -> none")
        print("Mouse input sent -> False")
        return 0

    layout_path = Path(args.layout)
    try:
        layout = ShopMouseLayout.load(layout_path)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    mouse = BalatroMouseController(armed=True)
    with ExternalShopMouseExecutor(layout, mouse=mouse) as executor:
        controller = ExternalShopController(
            observer,
            executor,
            translator=translator,
            policy=policy,
        )
        try:
            session = controller.open()
            ranked = controller.rank_actions(session)
        except (RuntimeError, ValueError) as error:
            parser.error(str(error))

        if not ranked:
            parser.error("no buffer-safe shop action is available")

        recommendation = ranked[0].action
        print(f"Save -> {reader.path}")
        print(f"Money before -> {session.state.money}")
        print_ranking(ranked, heading="Pre-execution ranking:")
        print(
            f"Recommended -> {recommendation.name}: {target_label(recommendation)}"
        )

        if recommendation.name == END_SHOP:
            print("Policy recommends leaving the shop; purchase execution aborted.")
            print("Mouse input sent -> False")
            return 2

        observed_label = item_label(recommendation)
        if observed_label != args.expect_label:
            parser.error(
                "recommendation changed before execution: "
                f"expected label={args.expect_label!r}, observed={observed_label!r}"
            )

        try:
            executed = controller.execute_recommended_purchase(session)
        except (RuntimeError, ValueError) as error:
            parser.error(str(error))

        print(f"Executed -> {executed.name}: {target_label(executed)}")
        print("Mouse input sent -> True")
        print(f"Projected money -> {session.state.money}")
        print("Checkpoint reconciliation -> pending until END_SHOP")

        reranked = controller.rank_actions(session)
        print_ranking(reranked, heading="Projected ranking after one purchase:")
        next_action = reranked[0].action if reranked else None
        if next_action is not None:
            print(f"Next recommendation -> {next_action.name}: {target_label(next_action)}")
        else:
            print("Next recommendation -> none")
        print("Automatic follow-up purchase -> False")

        should_finish = (
            args.finish_if_done
            and next_action is not None
            and next_action.name == END_SHOP
        )
        if not should_finish:
            print("Automatic END_SHOP -> False")
            return 0

        print("Automatic END_SHOP -> True (policy recommends stopping)")
        try:
            checkpoint_snapshot, checkpoint_state = controller.leave_shop(session)
        except (RuntimeError, TimeoutError, ValueError) as error:
            parser.error(str(error))

        print("Checkpoint reconciliation -> PASS")
        print(f"Persisted phase -> {checkpoint_snapshot.phase}")
        print(f"Persisted money -> {checkpoint_state.money}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
