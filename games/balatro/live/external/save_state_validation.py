from __future__ import annotations

import argparse

from games.balatro.live.translator import DefaultBalatroStateTranslator

from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


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
    print(
        f"hand[{len(state.hand)}] -> {hand}"
    )
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
        "Raw save retained -> "
        + str("raw_save" in snapshot.payload)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
