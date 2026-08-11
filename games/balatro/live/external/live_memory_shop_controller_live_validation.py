from __future__ import annotations

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
    try:
        with LiveMemoryBalatroObserver() as observer:
            controller = LiveMemoryShopController(observer)
            view = controller.observe()
            actions = controller.available_actions(view)
            ranked = controller.rank_actions(view)
    except Exception as error:
        print("Live-memory SHOP planner validation -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse movement sent -> False")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2

    print("Live-memory SHOP planner validation -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {view.snapshot.phase}")
    print(f"Money -> {view.state.money}")
    print("Mouse movement sent -> False")
    print("Mouse clicks sent -> False")
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
    print("Integrated external action execution armed -> False for this validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
