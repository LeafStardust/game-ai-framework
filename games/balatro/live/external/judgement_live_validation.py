from __future__ import annotations

import argparse
import time
from pathlib import Path

from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .consumable_mouse import ConsumableMouseLayout
from .judgement_mouse import ExternalJudgementMouseExecutor
from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


DEFAULT_LAYOUT = "balatro-consumable-mouse.json"


def _area_cards(snapshot, name: str) -> list[dict]:
    area = snapshot.payload.get(name) or {}
    cards = area.get("cards") if isinstance(area, dict) else None
    return [item for item in (cards or []) if isinstance(item, dict)]


def _card_fingerprint(card) -> tuple:
    return (
        getattr(card, "rank", None),
        getattr(card, "suit", None),
        getattr(card, "enhancement", None),
        getattr(card, "edition", None),
        getattr(card, "seal", None),
    )


def _item_id(item: dict):
    return item.get("live_id")


def verify_judgement_checkpoint(
    before_state,
    after_state,
    before_snapshot,
    after_snapshot,
    *,
    judgement_live_id,
) -> tuple[str | None, dict | None]:
    """Validate one Judgement use and return the newly created raw Joker item."""

    if after_state.phase != "SELECTING_HAND":
        return f"phase changed to {after_state.phase}, expected SELECTING_HAND", None
    if int(after_state.score) != int(before_state.score):
        return (
            f"score changed during Judgement use: {before_state.score} -> {after_state.score}",
            None,
        )
    if int(after_state.hands_remaining) != int(before_state.hands_remaining):
        return (
            "hands changed during Judgement use: "
            f"{before_state.hands_remaining} -> {after_state.hands_remaining}",
            None,
        )
    if int(after_state.discards_remaining) != int(before_state.discards_remaining):
        return (
            "discards changed during Judgement use: "
            f"{before_state.discards_remaining} -> {after_state.discards_remaining}",
            None,
        )

    before_hand = {
        getattr(card, "live_id", None): card
        for card in before_state.hand
        if getattr(card, "live_id", None) is not None
    }
    after_hand = {
        getattr(card, "live_id", None): card
        for card in after_state.hand
        if getattr(card, "live_id", None) is not None
    }
    if set(before_hand) != set(after_hand):
        return "hand live_id set changed during Judgement use", None
    for live_id, before_card in before_hand.items():
        if _card_fingerprint(after_hand[live_id]) != _card_fingerprint(before_card):
            return f"hand card live_id {live_id} changed during Judgement use", None

    before_consumables = _area_cards(before_snapshot, "consumables")
    after_consumables = _area_cards(after_snapshot, "consumables")
    if len(after_consumables) != len(before_consumables) - 1:
        return (
            "held consumable count did not decrease by exactly one: "
            f"{len(before_consumables)} -> {len(after_consumables)}",
            None,
        )
    if any(_item_id(item) == judgement_live_id for item in after_consumables):
        return "the consumed Judgement live_id is still present after the checkpoint", None

    before_jokers = _area_cards(before_snapshot, "jokers")
    after_jokers = _area_cards(after_snapshot, "jokers")
    if len(after_jokers) != len(before_jokers) + 1:
        return (
            "Joker count did not increase by exactly one: "
            f"{len(before_jokers)} -> {len(after_jokers)}",
            None,
        )

    before_ids = {_item_id(item) for item in before_jokers}
    after_ids = {_item_id(item) for item in after_jokers}
    if None in before_ids or None in after_ids:
        return "Joker checkpoint contains an item without a stable live_id", None
    if not before_ids.issubset(after_ids):
        return "an existing Joker live_id disappeared during Judgement use", None

    new_ids = after_ids - before_ids
    if len(new_ids) != 1:
        return f"expected exactly one new Joker live_id, found {len(new_ids)}", None
    new_id = next(iter(new_ids))
    new_item = next(item for item in after_jokers if _item_id(item) == new_id)
    return None, new_item


def _wait_for_judgement_checkpoint(
    observer,
    before_snapshot,
    *,
    judgement_live_id,
    timeout: float = 20.0,
    poll_interval: float = 0.05,
):
    """Wait through partial save writes until both Judgement effects are present."""

    before_joker_count = len(_area_cards(before_snapshot, "jokers"))
    before_sha = before_snapshot.payload.get("save_sha256")
    deadline = time.monotonic() + max(0.0, timeout)
    last_detail = "save has not changed"

    while time.monotonic() < deadline:
        candidate = observer.observe()
        if candidate.payload.get("save_sha256") == before_sha:
            last_detail = "save has not changed"
            if poll_interval > 0:
                time.sleep(poll_interval)
            continue

        if candidate.phase != "SELECTING_HAND":
            last_detail = f"phase={candidate.phase}"
            if poll_interval > 0:
                time.sleep(poll_interval)
            continue

        consumables = _area_cards(candidate, "consumables")
        jokers = _area_cards(candidate, "jokers")
        judgement_present = any(
            _item_id(item) == judgement_live_id for item in consumables
        )
        joker_delta = len(jokers) - before_joker_count
        if not judgement_present and joker_delta == 1:
            return candidate

        last_detail = (
            f"judgement_present={judgement_present}, joker_delta={joker_delta}"
        )
        if poll_interval > 0:
            time.sleep(poll_interval)

    raise TimeoutError(
        "timed out waiting for complete Judgement checkpoint; " + last_detail
    )


def _find_judgement(state):
    matches = [
        consumable
        for consumable in state.consumables
        if getattr(consumable, "name", None) == "Judgement"
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one held Judgement, found {len(matches)}"
        )
    return matches[0]


def _projection_status(raw_joker: dict) -> tuple[bool, str]:
    joker = LiveJokerFactory().create(raw_joker)
    if joker is None:
        label = raw_joker.get("label") or raw_joker.get("ability_name") or "unknown Joker"
        return False, f"{label} is not represented by the framework Joker factory"

    if not LiveJokerScoreProjector.supports(joker):
        label = raw_joker.get("label") or type(joker).__name__
        return False, f"{label} is not yet validated by the live Joker score projector"
    return True, "validated by the live Joker score projector"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and optionally execute one Judgement desperation checkpoint. "
            "The random Joker result is never predicted from hidden RNG."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()
    snapshot = observer.observe()
    state = translator.translate(snapshot)

    print(f"Save -> {reader.path}")
    print(f"Phase before -> {state.phase}")
    if state.phase != "SELECTING_HAND":
        parser.error(f"Balatro save is in {state.phase}, expected SELECTING_HAND")

    raw_joker_count = len(_area_cards(snapshot, "jokers"))
    print(f"Score before -> {state.score}")
    print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
    print(f"Hands before -> {state.hands_remaining}")
    print(f"Discards before -> {state.discards_remaining}")
    print(f"Owned Jokers before -> {raw_joker_count}")
    print(f"Held consumables -> {len(state.consumables)}")
    for index, consumable in enumerate(state.consumables):
        print(
            f"  C{index}: {getattr(consumable, 'name', type(consumable).__name__)} "
            f"(live_id={getattr(consumable, 'live_id', None)}, "
            f"area_index={getattr(consumable, 'area_index', None)})"
        )

    try:
        if raw_joker_count >= int(getattr(state, "joker_slots", 5)):
            raise RuntimeError("no authoritative Joker slot is available for Judgement")
        judgement = _find_judgement(state)
        ExternalJudgementMouseExecutor._validate(state, judgement)
        area_index = int(getattr(judgement, "area_index"))
    except (RuntimeError, TypeError, ValueError) as error:
        print("Execution guard -> BLOCKED")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 0

    print(f"Judgement slot -> area_index={area_index}")
    print("Judgement outcome model -> authoritative post-use checkpoint")
    print("Hidden RNG used -> False")
    print("Execution guard -> PASS")

    if not args.execute:
        print("Mouse input sent -> False")
        print("Dry run -> Judgement is executable, but no consumable was spent")
        return 0

    try:
        layout = ConsumableMouseLayout.load(Path(args.layout))
        layout.point_for_slot(area_index)
        layout.use_point_for_slot(area_index)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        parser.error(str(error))

    judgement_live_id = getattr(judgement, "live_id", None)
    latest = observer.observe()
    if latest.payload.get("save_sha256") != snapshot.payload.get("save_sha256"):
        print("Execution guard -> BLOCKED")
        print("Reason -> save changed before Judgement execution; re-run from checkpoint")
        print("Mouse input sent -> False")
        return 0

    print("Executing consumable -> Judgement")
    mouse = BalatroMouseController(armed=True)
    try:
        with ExternalJudgementMouseExecutor(layout, mouse=mouse) as executor:
            executor.dispatch(state, judgement)
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    print("Mouse input sent -> True")
    print("Waiting for save checkpoint -> Judgement consumed and one Joker created")
    try:
        persisted = _wait_for_judgement_checkpoint(
            observer,
            snapshot,
            judgement_live_id=judgement_live_id,
        )
    except TimeoutError as error:
        parser.error(str(error))

    after_state = translator.translate(persisted)
    reason, new_joker = verify_judgement_checkpoint(
        state,
        after_state,
        snapshot,
        persisted,
        judgement_live_id=judgement_live_id,
    )
    if reason is not None or new_joker is None:
        print("Checkpoint verified -> False")
        print(f"Reason -> {reason or 'new Joker could not be identified'}")
        print("Follow-up mouse input sent -> False")
        return 2

    label = new_joker.get("label") or new_joker.get("ability_name") or "unknown"
    print(f"Phase after -> {after_state.phase}")
    print(f"Score after -> {after_state.score}")
    print(f"Hands after -> {after_state.hands_remaining}")
    print(f"Discards after -> {after_state.discards_remaining}")
    print(f"Created Joker -> {label}")
    print(f"Created Joker live_id -> {_item_id(new_joker)}")
    print("Checkpoint verified -> True")

    supported, support_reason = _projection_status(new_joker)
    print(f"Live Joker projection -> {'PASS' if supported else 'BLOCKED'}")
    print(f"Projection reason -> {support_reason}")
    print("Follow-up mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
