from __future__ import annotations

"""Verify Ouija's whole-hand rank rewrite and permanent hand-size loss."""

from games.balatro.actions import SELECT_PACK_CARD
from games.balatro.live.injected import action_dispatcher


OUIJA = "Ouija"


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


def _rank(record: dict) -> str | None:
    value = record.get("value")
    if not isinstance(value, dict):
        return None
    rank = value.get("rank")
    return str(rank) if rank is not None else None


def _hand_limit(snapshot) -> int | None:
    value = _area(snapshot, "hand").get("limit")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _verify(before, after) -> None:
    before_limit = _hand_limit(before)
    after_limit = _hand_limit(after)
    if before_limit is None or after_limit is None or after_limit != before_limit - 1:
        raise action_dispatcher.InjectedActionPostconditionError(
            "Ouija verification requires public hand limit to decrease by exactly one"
        )

    before_hand = _cards(before, "hand")
    before_ids = tuple(
        _identity(record)
        for record in before_hand
        if _identity(record) is not None
    )
    if len(before_ids) != len(before_hand) or len(before_ids) <= 1:
        raise action_dispatcher.InjectedActionPostconditionError(
            "Ouija verification requires unique public identities for the pre-use hand"
        )

    # The pack may close immediately after selection, so verify the permanent owned
    # card records rather than requiring G.hand to remain populated in SHOP.
    owned_after = _cards(after, "owned_cards")
    if not owned_after:
        raise action_dispatcher.InjectedActionPostconditionError(
            "Ouija verification requires authoritative owned-card state after use"
        )
    by_id = {
        _identity(record): record
        for record in owned_after
        if _identity(record) is not None
    }
    rewritten = [by_id.get(live_id) for live_id in before_ids]
    if any(record is None for record in rewritten):
        raise action_dispatcher.InjectedActionPostconditionError(
            "Ouija verification could not resolve every rewritten hand card in owned deck"
        )

    ranks = {_rank(record) for record in rewritten}
    if None in ranks or len(ranks) != 1:
        raise action_dispatcher.InjectedActionPostconditionError(
            "Ouija verification requires every pre-use hand card to settle on one common rank"
        )


def install_ouija_dispatch_postcondition() -> None:
    dispatcher_class = action_dispatcher.LiveMemoryInjectedActionDispatcher
    if getattr(dispatcher_class, "_ouija_dispatch_postcondition_installed", False):
        return

    original_dispatch = dispatcher_class.dispatch

    def dispatch(self, action, *, state=None, snapshot=None):
        label = _choice_label(action) if action.name == SELECT_PACK_CARD else ""
        if label != OUIJA:
            return original_dispatch(self, action, state=state, snapshot=snapshot)
        result = original_dispatch(self, action, state=state, snapshot=snapshot)
        _verify(result.before, result.after)
        return result

    dispatcher_class.dispatch = dispatch
    dispatcher_class._ouija_dispatch_postcondition_installed = True
