from __future__ import annotations

import argparse

from games.balatro.actions import END_SHOP
from games.balatro.live.shop import BalatroShopActionGenerator
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


def _target_label(action) -> str:
    if action.name == END_SHOP:
        return "Next Round"

    target = action.target
    label = getattr(target, "label", getattr(target, "name", type(target).__name__))
    index = getattr(target, "area_index", None)
    price = getattr(target, "price", getattr(target, "cost", None))
    if isinstance(price, dict):
        price = price.get("buy")

    text = f"slot={index} {label}"
    if price is not None:
        text += f" ${price}"
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rank current buffer-safe Balatro shop actions without sending mouse input."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    args = parser.parse_args()

    reader = BalatroSaveReader(args.save, profile=args.profile)
    snapshot = SaveBalatroObserver(reader).observe()
    state = DefaultBalatroStateTranslator().translate(snapshot)

    if state.phase != "SHOP":
        parser.error(f"Balatro save is in {state.phase}, expected SHOP")

    actions = BalatroShopActionGenerator().generate_bufferable_actions(state)
    ranked = BalatroShopPolicy().rank_actions(state, actions)

    print(f"Save -> {reader.path}")
    print(f"Money -> {state.money}")
    print(f"Buffer-safe actions -> {len(ranked)}")

    for index, result in enumerate(ranked, start=1):
        action = result.action
        print(
            f"{index}. {action.name}: {_target_label(action)} "
            f"score={result.total:.3f} "
            f"utility={result.item_utility:.3f} "
            f"edition=+{result.edition_bonus:.3f} "
            f"price=-{result.price_penalty:.3f} "
            f"interest=-{result.interest_penalty:.3f} "
            f"reserve=-{result.reserve_penalty:.3f} "
            f"slot=-{result.slot_penalty:.3f}"
        )
        for note in result.notes:
            print(f"   note: {note}")

    if ranked:
        best = ranked[0].action
        print(f"Recommended -> {best.name}: {_target_label(best)}")
    else:
        print("Recommended -> none")

    print("Mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
