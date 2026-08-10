from __future__ import annotations

import argparse

from games.balatro.live.translator import DefaultBalatroStateTranslator

from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


def _item_label(item) -> str:
    label = getattr(item, "label", getattr(item, "name", type(item).__name__))
    price = getattr(item, "price", getattr(item, "cost", None))
    if isinstance(price, dict):
        price = price.get("buy")
    if price is None:
        return str(label)
    return f"{label} (${price})"


def _items(values) -> str:
    return ", ".join(_item_label(value) for value in values) or "none"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read vanilla Balatro save.jkr and print the translated framework state."
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    args = parser.parse_args()

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    snapshot = observer.observe()
    state = DefaultBalatroStateTranslator().translate(snapshot)

    blind_name = snapshot.payload.get("blind", {}).get("name")
    hand = ", ".join(
        f"{card.rank} {card.suit}"
        for card in state.hand
    ) or "none"
    jokers = ", ".join(
        str(getattr(joker, "label", type(joker).__name__))
        for joker in state.jokers
    ) or "none"

    print(f"Save -> {reader.path}")
    print(
        f"phase={state.phase} save_state={snapshot.payload.get('save_state')} "
        f"complete={snapshot.state_complete}"
    )
    print(
        f"deck={state.deck_name} stake={state.stake_name} "
        f"ante={state.ante} round={state.round}"
    )
    print(
        f"money={state.money} score={state.score} "
        f"blind={blind_name} target={state.blind_score}"
    )
    print(
        f"hands={state.hands_remaining} discards={state.discards_remaining} "
        f"hand_size={state.hand_size}"
    )
    print(f"hand[{len(state.hand)}] -> {hand}")
    print(f"jokers[{len(state.jokers)}] -> {jokers}")
    print(
        "areas -> "
        f"deck={snapshot.payload['cards']['count']} "
        f"hand={snapshot.payload['hand']['count']} "
        f"jokers={snapshot.payload['jokers']['count']} "
        f"consumables={snapshot.payload['consumables']['count']} "
        f"play={snapshot.payload['play']['count']} "
        f"discard={snapshot.payload['discard']['count']}"
    )
    print(
        "shop areas -> "
        f"cards={snapshot.payload['shop_jokers']['count']} "
        f"boosters={snapshot.payload['shop_boosters']['count']} "
        f"vouchers={snapshot.payload['shop_vouchers']['count']}"
    )
    print(f"shop_jokers[{len(state.shop_jokers)}] -> {_items(state.shop_jokers)}")
    print(
        f"shop_consumables[{len(state.shop_consumables)}] -> "
        f"{_items(state.shop_consumables)}"
    )
    print(f"shop_boosters[{len(state.shop_boosters)}] -> {_items(state.shop_boosters)}")
    print(f"shop_vouchers[{len(state.shop_vouchers)}] -> {_items(state.shop_vouchers)}")
    print(f"hidden_raw_save_exposed={'raw_save' in snapshot.payload}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
