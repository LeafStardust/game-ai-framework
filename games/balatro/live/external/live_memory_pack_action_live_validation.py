from __future__ import annotations

import argparse

from games.balatro.actions import SELECT_PACK_CARD, BalatroAction

from .live_memory_action_dispatcher import LiveMemoryActionDispatcher
from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _array_table_values,
    _primitive,
    _table_fields,
)


def _text(value):
    primitive = _primitive(value)
    return primitive if isinstance(primitive, str) else None


def _first(*values):
    for value in values:
        primitive = _primitive(value)
        if primitive is not None:
            return primitive
    return None


def _pack_choices(observer: LiveMemoryBalatroObserver) -> list[dict]:
    decoder, _, root = observer._root()
    area = _table_fields(decoder, root.get("pack_cards"))
    result: list[dict] = []

    for index, (_, address) in enumerate(_array_table_values(decoder, area.get("cards"))):
        fields = decoder.string_fields(address)
        ability = _table_fields(decoder, fields.get("ability"))
        config = _table_fields(decoder, fields.get("config"))
        center = _table_fields(decoder, config.get("center"))
        base = _table_fields(decoder, fields.get("base"))

        label = _first(
            fields.get("label"),
            ability.get("name"),
            center.get("name"),
        )
        ability_set = _first(ability.get("set"), center.get("set"))
        live_id = _first(
            fields.get("sort_id"),
            fields.get("playing_card"),
            fields.get("ID"),
        )
        rank = _first(base.get("value"), base.get("id"))
        suit = _text(base.get("suit"))

        result.append(
            {
                "index": index,
                "address": address,
                "label": label,
                "ability_set": ability_set,
                "live_id": live_id,
                "rank": rank,
                "suit": suit,
            }
        )
    return result


def _choice_text(choice: dict) -> str:
    parts = [f"{choice['index']}. {choice['label']!r}"]
    if choice.get("ability_set") is not None:
        parts.append(f"set={choice['ability_set']!r}")
    if choice.get("rank") is not None or choice.get("suit") is not None:
        parts.append(f"card={choice.get('rank')!r}/{choice.get('suit')!r}")
    parts.append(f"live_id={choice.get('live_id')!r}")
    parts.append(f"address=0x{choice['address']:x}")
    return "; ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the current live booster-pack choices. By default this is read-only. "
            "--execute-index N REALLY selects and takes the chosen pack card using normal "
            "mouse input through the integrated live action dispatcher."
        )
    )
    parser.add_argument(
        "--execute-index",
        type=int,
        metavar="N",
        help=(
            "REALLY click pack choice N and then click its generated confirm/use control. "
            "This consumes that pack choice."
        ),
    )
    args = parser.parse_args()
    if args.execute_index is not None and args.execute_index < 0:
        parser.error("--execute-index cannot be negative")

    try:
        with LiveMemoryBalatroObserver() as observer:
            before = observer.observe()
            if not before.phase.endswith("_PACK"):
                raise RuntimeError(f"Balatro is in {before.phase}, expected *_PACK")

            choices = _pack_choices(observer)
            if not choices:
                raise RuntimeError("G.pack_cards contains no visible pack choices")

            result = None
            chosen_before = None
            if args.execute_index is not None:
                matches = [c for c in choices if c["index"] == args.execute_index]
                if len(matches) != 1:
                    raise ValueError(
                        f"pack choice index {args.execute_index} is unavailable; "
                        f"visible indices={[c['index'] for c in choices]}"
                    )
                chosen_before = matches[0]
                dispatcher = LiveMemoryActionDispatcher(observer)
                result = dispatcher.dispatch(
                    BalatroAction(SELECT_PACK_CARD, target=args.execute_index),
                    snapshot=before,
                )
    except Exception as error:
        print("Live-memory pack action validation -> FAIL")
        print(f"Reason -> {error}")
        print(
            "Mouse movement/clicks may have been sent -> "
            f"{args.execute_index is not None}"
        )
        print("Process writes/injection -> False")
        return 2

    print("Live-memory pack action validation -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase before -> {before.phase}")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(f"Visible pack choices -> {len(choices)}")
    for choice in choices:
        print("  " + _choice_text(choice))

    if result is None:
        print("Mouse movement sent -> False")
        print("Mouse clicks sent -> False")
        print("Integrated pack action execution armed -> False for this validation")
        return 0

    details = result.details
    print("Integrated pack action execution armed -> True")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> True")
    print("Clicks sent -> 2")
    print(f"Executed action -> {result.action.name}")
    print(f"Chosen index -> {args.execute_index}")
    print(f"Chosen label -> {chosen_before['label']!r}")
    print(f"Chosen address -> 0x{chosen_before['address']:x}")
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


if __name__ == "__main__":
    raise SystemExit(main())
