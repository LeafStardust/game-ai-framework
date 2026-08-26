from __future__ import annotations

"""Verify Ectoplasm's Negative target and escalating permanent hand-size cost."""

from games.balatro.actions import SELECT_PACK_CARD
from games.balatro.live.injected import action_dispatcher


ECTOPLASM = "Ectoplasm"


def _area(snapshot, name: str) -> dict:
    value = snapshot.payload.get(name)
    return value if isinstance(value, dict) else {}


def _cards(snapshot, name: str) -> list[dict]:
    cards = _area(snapshot, name).get("cards")
    return [record for record in cards if isinstance(record, dict)] if isinstance(cards, list) else []


def _choice_label(action) -> str:
    target = getattr(action, "target", None)
    return str(getattr(target, "label", "") or "")


def _identity(record: dict):
    return record.get("live_id", record.get("id"))


def _edition_name(record: dict) -> str | None:
    edition = record.get("edition")
    if isinstance(edition, dict):
        for name, enabled in edition.items():
            if bool(enabled):
                return str(name).upper()
        return None
    if edition:
        return str(edition).upper()
    return None


def _hand_limit(snapshot) -> int | None:
    value = _area(snapshot, "hand").get("limit")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _ecto_minus(snapshot) -> int | None:
    value = snapshot.payload.get("ectoplasm_hand_size_penalty")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return max(1, int(value))


def _verify(before, after) -> None:
    penalty = _ecto_minus(before)
    after_penalty = _ecto_minus(after)
    if penalty is None or after_penalty is None or after_penalty != penalty + 1:
        raise action_dispatcher.InjectedActionPostconditionError(
            "Ectoplasm verification requires public ecto_minus to increment by exactly one"
        )

    before_limit = _hand_limit(before)
    after_limit = _hand_limit(after)
    if before_limit is None or after_limit is None or after_limit != before_limit - penalty:
        raise action_dispatcher.InjectedActionPostconditionError(
            "Ectoplasm verification requires hand limit to drop by the pre-use ecto_minus"
        )

    before_jokers = _cards(before, "jokers")
    after_jokers = _cards(after, "jokers")
    if len(after_jokers) != len(before_jokers):
        raise action_dispatcher.InjectedActionPostconditionError(
            "Ectoplasm verification requires Joker roster size to remain unchanged"
        )

    before_by_id = {
        _identity(record): record
        for record in before_jokers
        if _identity(record) is not None
    }
    after_by_id = {
        _identity(record): record
        for record in after_jokers
        if _identity(record) is not None
    }
    if len(before_by_id) != len(before_jokers) or set(before_by_id) != set(after_by_id):
        raise action_dispatcher.InjectedActionPostconditionError(
            "Ectoplasm verification requires stable public Joker identities"
        )

    changed = []
    for live_id, before_record in before_by_id.items():
        before_edition = _edition_name(before_record)
        after_edition = _edition_name(after_by_id[live_id])
        if before_edition != after_edition:
            changed.append((before_edition, after_edition))

    if changed != [(None, "NEGATIVE")]:
        raise action_dispatcher.InjectedActionPostconditionError(
            "Ectoplasm verification requires exactly one editionless Joker to become Negative"
        )


def install_ectoplasm_dispatch_postcondition() -> None:
    dispatcher_class = action_dispatcher.LiveMemoryInjectedActionDispatcher
    if getattr(dispatcher_class, "_ectoplasm_dispatch_postcondition_installed", False):
        return

    original_dispatch = dispatcher_class.dispatch

    def dispatch(self, action, *, state=None, snapshot=None):
        label = _choice_label(action) if action.name == SELECT_PACK_CARD else ""
        if label != ECTOPLASM:
            return original_dispatch(self, action, state=state, snapshot=snapshot)
        result = original_dispatch(self, action, state=state, snapshot=snapshot)
        _verify(result.before, result.after)
        return result

    dispatcher_class.dispatch = dispatch
    dispatcher_class._ectoplasm_dispatch_postcondition_installed = True
