from __future__ import annotations

"""Verify Wraith's public semantic result after injected pack execution."""

from games.balatro.actions import SELECT_PACK_CARD
from games.balatro.live.injected import action_dispatcher


WRAITH = "Wraith"


def _area_cards(snapshot, name: str) -> list[dict]:
    area = snapshot.payload.get(name)
    if not isinstance(area, dict):
        return []
    cards = area.get("cards")
    if not isinstance(cards, list):
        return []
    return [card for card in cards if isinstance(card, dict)]


def _choice_label(action) -> str:
    target = getattr(action, "target", None)
    return str(getattr(target, "label", "") or "")


def _identity(record: dict):
    return record.get("live_id", record.get("id"))


def _money(snapshot) -> int | None:
    value = snapshot.payload.get("money")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _verify(before, after) -> None:
    before_jokers = _area_cards(before, "jokers")
    after_jokers = _area_cards(after, "jokers")
    if len(after_jokers) != len(before_jokers) + 1:
        raise action_dispatcher.InjectedActionPostconditionError(
            "Wraith verification requires exactly one newly owned Joker"
        )

    before_ids = {_identity(record) for record in before_jokers if _identity(record) is not None}
    generated = [
        record
        for record in after_jokers
        if _identity(record) is not None and _identity(record) not in before_ids
    ]
    if len(generated) != 1:
        raise action_dispatcher.InjectedActionPostconditionError(
            "Wraith verification could not identify exactly one generated Joker"
        )
    if str(generated[0].get("rarity") or "").upper() != "RARE":
        raise action_dispatcher.InjectedActionPostconditionError(
            "Wraith generated Joker is not observed as Rare"
        )

    if _money(after) != 0:
        raise action_dispatcher.InjectedActionPostconditionError(
            "Wraith verification requires public money to settle at $0"
        )


def install_wraith_dispatch_postcondition() -> None:
    dispatcher_class = action_dispatcher.LiveMemoryInjectedActionDispatcher
    if getattr(dispatcher_class, "_wraith_dispatch_postcondition_installed", False):
        return

    original_dispatch = dispatcher_class.dispatch

    def dispatch(self, action, *, state=None, snapshot=None):
        label = _choice_label(action) if action.name == SELECT_PACK_CARD else ""
        if label != WRAITH:
            return original_dispatch(self, action, state=state, snapshot=snapshot)
        result = original_dispatch(self, action, state=state, snapshot=snapshot)
        _verify(result.before, result.after)
        return result

    dispatcher_class.dispatch = dispatch
    dispatcher_class._wraith_dispatch_postcondition_installed = True
