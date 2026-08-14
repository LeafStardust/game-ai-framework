from __future__ import annotations

import argparse
from dataclasses import dataclass

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.state import BalatroState

from .live_memory_observer import LiveMemoryBalatroObserver


@dataclass(frozen=True)
class LiveD9PackCandidate:
    score: PackActionScore
    kind: str
    label: str
    area_index: int | None


@dataclass(frozen=True)
class LiveD9PackView:
    snapshot: LiveBalatroSnapshot
    state: BalatroState
    choices: tuple[LivePackChoice, ...]
    candidates: tuple[LiveD9PackCandidate, ...]
    recommendation: LiveD9PackCandidate


def _candidate_from_score(score: PackActionScore) -> LiveD9PackCandidate:
    action = score.action
    if action.name == SKIP_BOOSTER:
        return LiveD9PackCandidate(
            score=score,
            kind="SKIP",
            label="Skip",
            area_index=None,
        )
    if action.name != SELECT_PACK_CARD or not isinstance(action.target, LivePackChoice):
        raise ValueError(f"unexpected D9 pack action {action.name!r}")
    choice = action.target
    return LiveD9PackCandidate(
        score=score,
        kind=choice.kind,
        label=str(choice.label or "<unknown>"),
        area_index=int(choice.area_index),
    )


def build_live_d9_view(
    snapshot: LiveBalatroSnapshot,
    state: BalatroState,
    choices: list[LivePackChoice] | tuple[LivePackChoice, ...],
    *,
    policy: BalatroPackPolicy | None = None,
    generator: LivePackActionGenerator | None = None,
) -> LiveD9PackView:
    if not str(state.phase).endswith("_PACK"):
        raise ValueError(
            f"D9 live validator requires a *_PACK phase, observed {state.phase}"
        )
    if not bool(snapshot.state_complete):
        raise ValueError(f"{snapshot.phase} is not complete; wait for the UI to settle")

    active_policy = policy or BalatroPackPolicy()
    active_generator = generator or LivePackActionGenerator()
    visible = tuple(choices)
    actions = active_generator.generate_actions(state, list(visible))
    ranked = active_policy.rank_actions(state, actions)
    if not ranked:
        raise ValueError("D9 pack policy produced no legal action")
    candidates = tuple(_candidate_from_score(result) for result in ranked)
    return LiveD9PackView(
        snapshot=snapshot,
        state=state,
        choices=visible,
        candidates=candidates,
        recommendation=candidates[0],
    )


def _print_candidate(candidate: LiveD9PackCandidate) -> None:
    score = candidate.score
    if candidate.area_index is None:
        identity = "Skip"
    else:
        identity = (
            f"index={candidate.area_index} label={candidate.label!r} "
            f"kind={candidate.kind}"
        )
    print(f"Candidate -> {identity} score={score.total:.3f}")
    if score.action.cards:
        print(f"  B6 target count={len(score.action.cards)}")
    for note in score.notes:
        print(f"  note: {note}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "D9 Balatro visible pack-choice policy validation. This command is "
            "strictly read-only: it observes the current pack, scores every visible "
            "offer against Skip, prints the B3/B4/B6 rationale, and executes no "
            "gameplay action."
        )
    )
    parser.parse_args()

    translator = DefaultBalatroStateTranslator()
    generator = LivePackActionGenerator()

    with LiveMemoryBalatroObserver() as observer:
        snapshot = observer.observe()
        if not snapshot.phase.endswith("_PACK"):
            parser.error(
                f"D9 pack policy validation requires a *_PACK phase, observed "
                f"{snapshot.phase}"
            )
        if not snapshot.state_complete:
            parser.error(f"{snapshot.phase} is not complete; wait for the UI to settle")

        choices = generator.read_choices(observer)
        state = translator.translate(snapshot)
        try:
            view = build_live_d9_view(snapshot, state, choices, generator=generator)
        except ValueError as error:
            parser.error(str(error))

        print("Live-memory D9 pack policy validation -> READY")
        print("Observation source -> live Balatro process memory")
        print(f"Phase -> {state.phase}")
        print(f"Visible choices -> {len(view.choices)}")
        print("Skip baseline -> explicit")
        for candidate in view.candidates:
            _print_candidate(candidate)

        recommendation = view.recommendation
        if recommendation.area_index is None:
            print("Recommended D9 action -> SKIP")
        else:
            print(
                f"Recommended D9 action -> SELECT index={recommendation.area_index} "
                f"{recommendation.label!r} kind={recommendation.kind}"
            )
            if recommendation.score.action.cards:
                print(
                    "Resolved B6 target carried by recommendation -> "
                    f"{len(recommendation.score.action.cards)} card(s)"
                )

        print("Execution guard -> PREVIEW ONLY")
        print("Injected bridge command sent -> False")
        print("Gameplay action executed -> False")
        print("Mouse input sent -> False")
        print("Observation process writes -> False")
        print("Hidden RNG/deck traversal -> False")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
