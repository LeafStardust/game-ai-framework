from __future__ import annotations

import argparse

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER

from .live_memory_observer import LiveMemoryBalatroObserver
from .live_memory_pack_controller import LiveMemoryPackController


def _choice_text(choice) -> str:
    data = choice.data
    parts = [f"{choice.area_index}. {choice.label!r}"]
    parts.append(f"set={choice.kind!r}")
    value = data.get("value") or {}
    if value.get("rank") is not None or value.get("suit") is not None:
        parts.append(f"card={value.get('rank')!r}/{value.get('suit')!r}")
    parts.append(f"live_id={choice.live_id!r}")
    parts.append(f"address=0x{choice.address:x}")
    return "; ".join(parts)


def _action_text(action) -> str:
    if action.name == SKIP_BOOSTER:
        return "SKIP_BOOSTER"
    choice = action.target
    return f"{action.name}: index={choice.area_index}, label={choice.label!r}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect and rank the current live booster pack. By default this is read-only. "
            "Armed options REALLY click/consume a pack action through the integrated dispatcher."
        )
    )
    armed = parser.add_mutually_exclusive_group()
    armed.add_argument(
        "--execute-index",
        type=int,
        metavar="N",
        help=(
            "REALLY click pack choice N and its generated confirm/use control. "
            "This consumes that pack choice."
        ),
    )
    armed.add_argument(
        "--execute-recommended",
        action="store_true",
        help="REALLY execute the pack policy's recommended choice or Skip action.",
    )
    armed.add_argument(
        "--execute-skip",
        action="store_true",
        help="REALLY click Skip and forfeit the current booster pack choice(s).",
    )
    args = parser.parse_args()
    if args.execute_index is not None and args.execute_index < 0:
        parser.error("--execute-index cannot be negative")
    armed_execution = (
        args.execute_index is not None
        or args.execute_recommended
        or args.execute_skip
    )

    try:
        with LiveMemoryBalatroObserver() as observer:
            controller = LiveMemoryPackController(observer)
            view = controller.observe()
            actions = controller.available_actions(view)
            ranked = controller.rank_actions(view)

            result = None
            chosen_action = None
            if args.execute_index is not None:
                chosen_action = next(
                    (
                        action
                        for action in actions
                        if action.name == SELECT_PACK_CARD
                        and int(action.target.area_index) == args.execute_index
                    ),
                    None,
                )
                if chosen_action is None:
                    raise ValueError(
                        f"pack choice index {args.execute_index} is unavailable; "
                        f"visible indices={[choice.area_index for choice in view.choices]}"
                    )
                result = controller.execute(chosen_action, view)
            elif args.execute_recommended:
                chosen_action = controller.recommended_action(view)
                result = controller.execute(chosen_action, view)
            elif args.execute_skip:
                chosen_action = next(
                    (action for action in actions if action.name == SKIP_BOOSTER),
                    None,
                )
                if chosen_action is None:
                    raise RuntimeError("SKIP_BOOSTER is not available")
                result = controller.execute(chosen_action, view)
    except Exception as error:
        print("Live-memory pack action validation -> FAIL")
        print(f"Reason -> {error}")
        print(f"Mouse movement/clicks may have been sent -> {armed_execution}")
        print("Process writes/injection -> False")
        return 2

    print("Live-memory pack action validation -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase before -> {view.snapshot.phase}")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(f"Visible pack choices -> {len(view.choices)}")
    for choice in view.choices:
        print("  " + _choice_text(choice))

    print(f"Available pack actions -> {len(actions)}")
    for action in actions:
        print("  " + _action_text(action))

    print(f"Policy-ranked actions -> {len(ranked)}")
    for index, score in enumerate(ranked, start=1):
        notes = "; ".join(score.notes)
        suffix = f"; {notes}" if notes else ""
        print(f"  {index}. {_action_text(score.action)}; score={score.total:.3f}{suffix}")
    if ranked:
        print(f"Recommended action -> {_action_text(ranked[0].action)}")

    if result is None:
        print("Mouse movement sent -> False")
        print("Mouse clicks sent -> False")
        print("Integrated pack action execution armed -> False for this validation")
        return 0

    print("Integrated pack action execution armed -> True")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> True")
    print(f"Executed action -> {result.action.name}")

    if result.action.name == SELECT_PACK_CARD:
        details = result.details
        choice = result.action.target
        print("Clicks sent -> 2")
        print(f"Chosen index -> {choice.area_index}")
        print(f"Chosen label -> {choice.label!r}")
        print(f"Chosen address -> 0x{choice.address:x}")
        print(
            "Selection click -> "
            f"x={details.selection_point.x} y={details.selection_point.y}"
        )
        print(f"Confirm button -> {details.confirm.button!r}")
        print(f"Confirm func -> {details.confirm.func!r}")
        print(f"Confirm location source -> {details.confirm.location_source}")
        print(f"Confirm probes required -> {details.confirm.probes}")
        print(f"Confirm local search used -> {details.confirm.used_local_search}")
        print(f"Confirm fallback search used -> {details.confirm.used_fallback_search}")
        print(f"Phase after -> {result.after.phase}")
        print(f"Selected card consumed from pack -> {details.selected_card_consumed}")
        print("Integrated SELECT_PACK_CARD checkpoint verified -> True")
        return 0

    details = result.details
    print("Clicks sent -> 1")
    print(f"Skip button -> {details.button!r}")
    print(f"Skip func -> {details.func!r}")
    print(f"Skip location source -> {details.location_source}")
    print(f"Skip probes required -> {details.probes}")
    print(f"Phase after -> {result.after.phase}")
    print("Integrated SKIP_BOOSTER checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
