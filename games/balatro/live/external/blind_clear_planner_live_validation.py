from __future__ import annotations

import argparse

from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.external.save_observer import SaveBalatroObserver
from games.balatro.live.external.save_state import BalatroSaveReader
from games.balatro.live.translator import DefaultBalatroStateTranslator


def _indices(state, action) -> tuple[int, ...]:
    identities = {id(card) for card in action.cards}
    return tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in identities
    )


def _card_text(card) -> str:
    parts = [str(card.rank), str(card.suit)]
    if getattr(card, "enhancement", None):
        parts.append(str(card.enhancement))
    if getattr(card, "edition", None):
        parts.append(str(card.edition))
    if getattr(card, "seal", None):
        parts.append(str(card.seal))
    return " / ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read the vanilla Balatro save and preview the bounded public-state "
            "blind-clear planner. This validator never sends mouse input."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--play-width", type=int, default=6)
    parser.add_argument("--discard-width", type=int, default=4)
    parser.add_argument("--samples", type=int, default=256)
    args = parser.parse_args()

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    snapshot = observer.observe()
    state = DefaultBalatroStateTranslator().translate(snapshot)

    print(f"Save -> {reader.path}")
    print(f"Phase -> {state.phase}")
    print(f"Score -> {state.score}")
    print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
    print(f"Hands -> {state.hands_remaining}")
    print(f"Discards -> {state.discards_remaining}")
    print(f"Visible hand cards -> {len(state.hand)}")
    print(f"Public remaining deck cards -> {len(state.deck)}")

    if state.phase != "SELECTING_HAND":
        print("Planner ready -> False")
        print(f"Reason -> current phase is {state.phase}")
        print("Mouse input sent -> False")
        return 0

    from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel

    planner = LiveBlindClearPlanner(
        draw_outcomes=PublicDrawOutcomeModel(sample_count=args.samples),
        play_width=args.play_width,
        discard_width=args.discard_width,
        horizon=2,
    )
    try:
        plan = planner.plan(state)
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    indices = _indices(state, plan.action)
    print(f"Recommended -> {plan.action.name}")
    print("Selected indices -> " + ",".join(str(index) for index in indices))
    for index in indices:
        print(f"  {index}: {_card_text(state.hand[index])}")
    print(f"Two-action clear probability -> {plan.value.clear_probability:.6f}")
    print(f"Expected horizon progress -> {plan.value.expected_progress:.6f}")
    print(f"Expected horizon score -> {plan.value.expected_score:.3f}")
    print(f"Expected hands remaining -> {plan.value.expected_hands_remaining:.3f}")
    print(f"Expected discards remaining -> {plan.value.expected_discards_remaining:.3f}")
    print(f"Candidate actions evaluated -> {plan.candidate_count}")
    print(f"Draw branches exact -> {plan.exact}")
    print("Planner horizon -> 2 actions")
    print("Hidden draw order used -> False")
    print("Mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
