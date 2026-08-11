from __future__ import annotations

from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.playbook import (
    BalatroPlaybookNotFound,
    default_balatro_playbooks,
)

from .live_memory_observer import LiveMemoryBalatroObserver


def _card_text(card: dict) -> str:
    value = card.get("value") or {}
    modifier = card.get("modifier") or {}
    parts = [
        str(value.get("rank") or "?"),
        str(value.get("suit") or "?"),
    ]
    for name in ("enhancement", "edition", "seal"):
        value = modifier.get(name)
        if value:
            parts.append(str(value))
    live_id = card.get("live_id")
    if live_id is not None:
        parts.append(f"live_id={live_id}")
    return " / ".join(parts)


def _item_text(item: dict) -> str:
    label = item.get("label") or item.get("ability_name") or item.get("center") or "?"
    extras = []
    if item.get("live_id") is not None:
        extras.append(f"live_id={item['live_id']}")
    if item.get("area_index") is not None:
        extras.append(f"area_index={item['area_index']}")
    suffix = f" ({', '.join(extras)})" if extras else ""
    return f"{label}{suffix}"


def main() -> int:
    try:
        with LiveMemoryBalatroObserver() as observer:
            snapshot = observer.observe()
    except Exception as error:
        print("Live-memory state validation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    payload = snapshot.payload
    round_info = payload.get("round") or {}

    print("Live-memory state validation -> PASS")
    print("Observation source -> live Balatro process memory")
    print("save.jkr used -> False")
    print("Process writes/injection -> False")
    print(f"Hidden RNG exposed -> {payload.get('hidden_rng_exposed')}")
    print(f"Hidden draw order exposed -> {payload.get('hidden_draw_order_exposed')}")
    print(f"Snapshot sequence -> {snapshot.sequence}")
    print(f"Phase -> {snapshot.phase}")
    print(f"State complete -> {snapshot.state_complete}")
    print(f"Deck -> {payload.get('deck')}")
    print(f"Stake -> {payload.get('stake')}")
    print(f"Ante -> {payload.get('ante_num')}")
    print(f"Round -> {payload.get('round_num')}")
    print(f"Money -> {payload.get('money')}")
    print(f"Score -> {payload.get('score')}")
    print(f"Blind target -> {round_info.get('chips')}")
    print(f"Hands -> {round_info.get('hands_left')}")
    print(f"Discards -> {round_info.get('discards_left')}")

    hand = (payload.get("hand") or {}).get("cards") or []
    print(f"Hand -> {len(hand)} cards")
    for index, card in enumerate(hand):
        print(f"  H{index}: {_card_text(card)}")

    deck = (payload.get("cards") or {}).get("cards") or []
    print(f"Public remaining deck -> {len(deck)} cards (canonical order; future draw order destroyed)")

    jokers = (payload.get("jokers") or {}).get("cards") or []
    print(f"Jokers -> {len(jokers)}")
    for index, item in enumerate(jokers):
        print(f"  J{index}: {_item_text(item)}")

    consumables = (payload.get("consumables") or {}).get("cards") or []
    print(f"Consumables -> {len(consumables)}")
    for index, item in enumerate(consumables):
        print(f"  C{index}: {_item_text(item)}")

    for key, label in (
        ("shop_jokers", "Shop cards"),
        ("shop_boosters", "Shop boosters"),
        ("shop_vouchers", "Shop vouchers"),
    ):
        items = (payload.get(key) or {}).get("cards") or []
        print(f"{label} -> {len(items)}")
        for index, item in enumerate(items):
            print(f"  {index}: {_item_text(item)}")

    try:
        state = DefaultBalatroStateTranslator().translate(snapshot)
        playbook = default_balatro_playbooks().for_state(state)
    except BalatroPlaybookNotFound as error:
        print("Playbook selection -> BLOCKED")
        print(f"Reason -> {error}")
        return 0
    except Exception as error:
        print("State translation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print("State translation -> PASS")
    print(f"Playbook selection -> {playbook.name} v{playbook.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
