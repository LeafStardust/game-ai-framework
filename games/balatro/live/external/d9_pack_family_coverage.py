from __future__ import annotations

import argparse
import json
from pathlib import Path

from games.balatro.actions import SKIP_BOOSTER
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.pack_policy import BalatroPackPolicy

from .live_memory_observer import LiveMemoryBalatroObserver
from .live_memory_pack_policy_validation import build_live_d9_view


REQUIRED_FAMILIES = ("JOKER", "STANDARD", "PLANET", "TAROT", "SPECTRAL")
KIND_TO_FAMILY = {
    "JOKER": "JOKER",
    "PLAYING_CARD": "STANDARD",
    "PLANET": "PLANET",
    "TAROT": "TAROT",
    "SPECTRAL": "SPECTRAL",
}
DEFAULT_OUTPUT = Path("logs/balatro/d9-pack-family-coverage.jsonl")


def classify_pack_family(choices: tuple[LivePackChoice, ...] | list[LivePackChoice]) -> str:
    """Map one visible homogeneous booster choice set to the D9 family contract."""
    families = {
        KIND_TO_FAMILY.get(str(choice.kind).upper())
        for choice in choices
        if KIND_TO_FAMILY.get(str(choice.kind).upper()) is not None
    }
    if len(families) != 1:
        raise ValueError(
            "D9 family coverage requires one recognizable homogeneous pack family; "
            f"observed={sorted(family for family in families if family is not None)}"
        )
    return next(iter(families))


def _selected_card_indices(state, action) -> tuple[int, ...]:
    selected_ids = {id(card) for card in action.cards}
    return tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in selected_ids
    )


def record_from_view(view) -> dict:
    family = classify_pack_family(view.choices)
    recommendation = view.recommendation
    action = recommendation.score.action
    return {
        "sequence": int(view.snapshot.sequence),
        "phase": str(view.snapshot.phase),
        "family": family,
        "recommendation": {
            "action": str(action.name),
            "kind": str(recommendation.kind),
            "label": str(recommendation.label),
            "area_index": recommendation.area_index,
            "score": float(recommendation.score.total),
            "target_indices": list(_selected_card_indices(view.state, action)),
            "notes": list(recommendation.score.notes),
        },
        "candidates": [
            {
                "action": str(candidate.score.action.name),
                "kind": str(candidate.kind),
                "label": str(candidate.label),
                "area_index": candidate.area_index,
                "score": float(candidate.score.total),
                "notes": list(candidate.score.notes),
            }
            for candidate in view.candidates
        ],
    }


def append_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
        handle.write("\n")


def load_records(path: Path) -> tuple[dict, ...]:
    if not path.exists():
        return ()
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid D9 family coverage JSONL at line {line_number}: {error}"
                ) from error
            if isinstance(record, dict):
                records.append(record)
    return tuple(records)


def coverage_summary(records: tuple[dict, ...] | list[dict]) -> dict:
    observed = tuple(
        family
        for family in REQUIRED_FAMILIES
        if any(record.get("family") == family for record in records)
    )
    missing = tuple(family for family in REQUIRED_FAMILIES if family not in observed)
    return {
        "observed": observed,
        "missing": missing,
        "complete": not missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only D9 live pack-family coverage recorder. Records the current "
            "policy recommendation and rationale without dispatching gameplay input."
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    translator = DefaultBalatroStateTranslator()
    generator = LivePackActionGenerator()
    policy = BalatroPackPolicy()

    with LiveMemoryBalatroObserver() as observer:
        snapshot = observer.observe()
        if not snapshot.phase.endswith("_PACK"):
            parser.error(
                f"D9 family coverage requires a *_PACK phase, observed {snapshot.phase}"
            )
        if not snapshot.state_complete:
            parser.error(f"{snapshot.phase} is not complete; wait for the UI to settle")

        choices = generator.read_choices(observer)
        state = translator.translate(snapshot)
        view = build_live_d9_view(
            snapshot,
            state,
            choices,
            generator=generator,
            policy=policy,
        )
        record = record_from_view(view)
        append_record(args.output, record)

    summary = coverage_summary(load_records(args.output))
    recommendation = record["recommendation"]
    print("D9 pack-family validation record -> SAVED")
    print(f"Family -> {record['family']}")
    print(
        "Recommendation -> "
        f"{recommendation['action']} {recommendation['label']!r} "
        f"score={recommendation['score']:.3f}"
    )
    print(f"Coverage observed -> {', '.join(summary['observed']) or '<none>'}")
    print(f"Coverage missing -> {', '.join(summary['missing']) or '<none>'}")
    print(f"All five D9 families observed -> {summary['complete']}")
    print("Gameplay action executed -> False")
    print("Hidden RNG/deck traversal -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
