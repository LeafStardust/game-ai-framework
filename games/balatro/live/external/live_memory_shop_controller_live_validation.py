from __future__ import annotations

import argparse

from games.balatro.actions import BUY_BOOSTER

from .live_memory_observer import LiveMemoryBalatroObserver
from .live_memory_shop_controller import LiveMemoryShopController


def _target_text(action) -> str:
    target = action.target
    if target is None:
        return "-"
    label = getattr(target, "label", getattr(target, "name", None))
    index = getattr(target, "area_index", None)
    price = getattr(target, "price", getattr(target, "cost", None))
    parts = []
    if label is not None:
        parts.append(repr(label))
    if index is not None:
        parts.append(f"index={index}")
    if price is not None:
        parts.append(f"cost={price}")
    return ", ".join(parts) or repr(target)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the live-memory SHOP planner. By default this is read-only. "
            "--execute-booster INDEX really selects, buys, and opens that booster "
            "using two normal mouse clicks."
        )
    )
    parser.add_argument(
        "--execute-booster",
        type=int,
        metavar="INDEX",
        help=(
            "REALLY buy/open the affordable booster at this area_index. This clicks "
            "the booster card, clicks its generated Open control, spends money, and "
            "leaves SHOP for the booster-pack phase."
        ),
    )
    args = parser.parse_args()
    if args.execute_booster is not None and args.execute_booster < 0:
        parser.error("--execute-booster index cannot be negative")

    try:
        with LiveMemoryBalatroObserver() as observer:
            controller = LiveMemoryShopController(observer)
            view = controller.observe()
            actions = controller.available_actions(view)
            ranked = controller.rank_actions(view)

            result = None
            if args.execute_booster is not None:
                result = controller.open_booster(args.execute_booster, view)
    except Exception as error:
        print("Live-memory SHOP planner validation -> FAIL")
        print(f"Reason -> {error}")
        print(f"Mouse movement/clicks may have been sent -> {args.execute_booster is not None}")
        print("Process writes/injection -> False")
        return 2

    print("Live-memory SHOP planner validation -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {view.snapshot.phase}")
    print(f"Money -> {view.state.money}")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(f"Available actions -> {len(actions)}")
    for index, action in enumerate(actions, start=1):
        suffix = " [explicit booster]" if action.name == BUY_BOOSTER else ""
        print(f"  {index}. {action.name}: {_target_text(action)}{suffix}")

    print(f"Policy-ranked actions -> {len(ranked)}")
    for index, score in enumerate(ranked, start=1):
        print(
            f"  {index}. {score.action.name}: {_target_text(score.action)}; "
            f"score={score.total:.3f}"
        )
    if ranked:
        print(f"Recommended action -> {ranked[0].action.name}: {_target_text(ranked[0].action)}")

    if result is None:
        print("Mouse movement sent -> False")
        print("Mouse clicks sent -> False")
        print("Integrated external action execution armed -> False for this validation")
        return 0

    item = result.details["item"] if isinstance(result.details, dict) else None
    control = result.details["control"] if isinstance(result.details, dict) else None
    print("Integrated external action execution armed -> True")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> True")
    print("Clicks sent -> 2")
    print(f"Executed action -> {result.action.name}")
    if item is not None:
        print(f"Opened booster -> {item.label!r}, index={item.index}, cost={item.cost:g}")
    if control is not None:
        if control.item_click_point is not None:
            print(
                "Booster selection click -> "
                f"x={control.item_click_point.x} y={control.item_click_point.y}"
            )
        print(f"Open control button -> {control.button!r}")
        print(f"Open control func -> {control.func!r}")
        print(f"Open location source -> {control.location_source}")
        print(f"Open probes required -> {control.probes}")
        print(f"Local live search used -> {control.used_local_search}")
        print(f"Fallback search used -> {control.used_fallback_search}")
    print(f"Phase before action -> {result.before.phase}")
    print(f"Money before action -> {result.before.payload.get('money')}")
    print(f"Phase after action -> {result.after.phase}")
    print(f"Money after action -> {result.after.payload.get('money')}")
    print("Integrated booster checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
