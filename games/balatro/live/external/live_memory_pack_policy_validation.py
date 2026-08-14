from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.injected import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.state import BalatroState

from .live_memory_observer import LiveMemoryBalatroObserver


_ACTIONS = (SELECT_PACK_CARD, SKIP_BOOSTER)


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


def _choice_detail(choice: LivePackChoice) -> str:
    details: list[str] = []
    value = choice.data.get("value") or {}
    modifier = choice.data.get("modifier") or {}

    rank = value.get("rank")
    suit = value.get("suit")
    if rank is not None or suit is not None:
        details.append(f"card={rank}/{suit}")

    for name in ("enhancement", "edition", "seal"):
        modifier_value = modifier.get(name)
        if modifier_value:
            details.append(f"{name}={modifier_value}")

    center = choice.data.get("center")
    if center:
        details.append(f"center={center}")

    return " | ".join(details)


def _print_candidate(candidate: LiveD9PackCandidate) -> None:
    score = candidate.score
    choice = score.action.target if isinstance(score.action.target, LivePackChoice) else None
    if candidate.area_index is None:
        identity = "Skip"
    else:
        identity = (
            f"index={candidate.area_index} label={candidate.label!r} "
            f"kind={candidate.kind}"
        )
        if choice is not None:
            detail = _choice_detail(choice)
            if detail:
                identity += f" | {detail}"
    print(f"Candidate -> {identity} score={score.total:.3f}")
    if score.action.cards:
        print(f"  B6 target count={len(score.action.cards)}")
    for note in score.notes:
        print(f"  note: {note}")


def _selected_card_indices(state: BalatroState, action: BalatroAction) -> tuple[int, ...]:
    selected_ids = {id(card) for card in action.cards}
    return tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in selected_ids
    )


def _semantic_payload(value):
    if isinstance(value, dict):
        return {
            key: _semantic_payload(item)
            for key, item in value.items()
            if key != "ui"
        }
    if isinstance(value, list):
        return [_semantic_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_semantic_payload(item) for item in value)
    return value


def _same_semantic_snapshot(
    expected: LiveBalatroSnapshot,
    current: LiveBalatroSnapshot,
) -> bool:
    return (
        current.phase == expected.phase
        and current.state_complete == expected.state_complete
        and _semantic_payload(current.payload) == _semantic_payload(expected.payload)
    )


def _choice_signature(
    choices: list[LivePackChoice] | tuple[LivePackChoice, ...],
) -> tuple[tuple, ...]:
    return tuple(
        (
            int(choice.area_index),
            int(choice.address),
            choice.live_id,
            str(choice.kind),
            str(choice.label or ""),
            json.dumps(
                _semantic_payload(choice.data),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            ),
        )
        for choice in choices
    )


def _recommendation_signature(
    view: LiveD9PackView,
) -> tuple[str, int | None, str, str | None, tuple[int, ...]]:
    candidate = view.recommendation
    action = candidate.score.action
    center = None
    if isinstance(action.target, LivePackChoice):
        center_value = action.target.data.get("center")
        center = str(center_value) if center_value is not None else None
    return (
        action.name,
        candidate.area_index,
        candidate.label,
        center,
        _selected_card_indices(view.state, action),
    )


def _execution_guard_errors(
    view: LiveD9PackView,
    *,
    expected_phase: str,
    expected_action: str,
    expected_index: int | None,
    expected_label: str | None,
    expected_center: str | None,
) -> list[str]:
    errors: list[str] = []
    candidate = view.recommendation
    action = candidate.score.action

    if view.snapshot.phase != expected_phase:
        errors.append(
            f"expected phase {expected_phase}, observed {view.snapshot.phase}"
        )
    if action.name != expected_action:
        errors.append(
            f"expected D9 recommendation {expected_action}, observed {action.name}"
        )

    if expected_action == SKIP_BOOSTER:
        return errors

    if candidate.area_index != expected_index:
        errors.append(
            f"expected recommended index {expected_index}, observed {candidate.area_index}"
        )
    if candidate.label != expected_label:
        errors.append(
            f"expected recommended label {expected_label!r}, observed {candidate.label!r}"
        )

    choice = action.target if isinstance(action.target, LivePackChoice) else None
    observed_center = (
        str(choice.data.get("center"))
        if choice is not None and choice.data.get("center") is not None
        else None
    )
    if observed_center != expected_center:
        errors.append(
            f"expected recommended center {expected_center!r}, observed {observed_center!r}"
        )
    return errors


def _print_recommendation(view: LiveD9PackView) -> None:
    recommendation = view.recommendation
    if recommendation.area_index is None:
        print("Recommended D9 action -> SKIP")
        return

    print(
        f"Recommended D9 action -> SELECT index={recommendation.area_index} "
        f"{recommendation.label!r} kind={recommendation.kind}"
    )
    action = recommendation.score.action
    if action.cards:
        indices = _selected_card_indices(view.state, action)
        print(
            "Resolved B6 target carried by recommendation -> "
            f"{len(action.cards)} card(s)"
        )
        print(f"Resolved B6 target indices -> {indices}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "D9 Balatro visible pack-choice policy validation. Preview mode is "
            "strictly read-only. --execute is guarded and dispatches exactly the "
            "current top D9 policy recommendation, preserving any resolved B6 "
            "playing-card targets carried by that recommendation."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expect-phase")
    parser.add_argument("--expect-action", choices=_ACTIONS)
    parser.add_argument("--expect-index", type=int)
    parser.add_argument("--expect-label")
    parser.add_argument("--expect-center")
    args = parser.parse_args()

    select_fields = (args.expect_index, args.expect_label, args.expect_center)
    if args.execute:
        if args.expect_phase is None or args.expect_action is None:
            parser.error("--execute requires --expect-phase and --expect-action")
        if args.expect_action == SELECT_PACK_CARD:
            if any(value is None for value in select_fields):
                parser.error(
                    "SELECT_PACK_CARD execution requires --expect-index, "
                    "--expect-label, and --expect-center"
                )
        elif any(value is not None for value in select_fields):
            parser.error(
                "SKIP_BOOSTER does not accept --expect-index, --expect-label, "
                "or --expect-center"
            )
    elif any(
        value is not None
        for value in (
            args.expect_phase,
            args.expect_action,
            args.expect_index,
            args.expect_label,
            args.expect_center,
        )
    ):
        parser.error("execution expectations are only valid with --execute")

    translator = DefaultBalatroStateTranslator()
    generator = LivePackActionGenerator()
    policy = BalatroPackPolicy()

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
            view = build_live_d9_view(
                snapshot,
                state,
                choices,
                generator=generator,
                policy=policy,
            )
        except ValueError as error:
            parser.error(str(error))

        print("Live-memory D9 pack policy validation -> READY")
        print("Observation source -> live Balatro process memory")
        print(f"Phase -> {state.phase}")
        print(f"Visible choices -> {len(view.choices)}")
        print("Skip baseline -> explicit")
        for candidate in view.candidates:
            _print_candidate(candidate)
        _print_recommendation(view)

        if not args.execute:
            print("Execution guard -> PREVIEW ONLY")
            print("Injected bridge command sent -> False")
            print("Gameplay action executed -> False")
            print("Mouse input sent -> False")
            print("Observation process writes -> False")
            print("Hidden RNG/deck traversal -> False")
            return 0

        assert args.expect_phase is not None
        assert args.expect_action is not None
        errors = _execution_guard_errors(
            view,
            expected_phase=args.expect_phase,
            expected_action=args.expect_action,
            expected_index=args.expect_index,
            expected_label=args.expect_label,
            expected_center=args.expect_center,
        )
        if errors:
            print("Execution guard -> BLOCKED")
            for error in errors:
                print(f"Reason -> {error}")
            print("Injected bridge command sent -> False")
            print("Gameplay action executed -> False")
            print("Mouse input sent -> False")
            print("Observation process writes -> False")
            print("Hidden RNG/deck traversal -> False")
            return 0

        latest_snapshot = observer.observe()
        latest_choices = generator.read_choices(observer)
        if (
            not _same_semantic_snapshot(snapshot, latest_snapshot)
            or _choice_signature(choices) != _choice_signature(latest_choices)
        ):
            print("Execution guard -> BLOCKED")
            print(
                "Reason -> live booster-pack state changed before dispatch; "
                "re-run from the new checkpoint"
            )
            print("Injected bridge command sent -> False")
            print("Gameplay action executed -> False")
            print("Mouse input sent -> False")
            print("Observation process writes -> False")
            print("Hidden RNG/deck traversal -> False")
            return 0

        latest_state = translator.translate(latest_snapshot)
        try:
            latest_view = build_live_d9_view(
                latest_snapshot,
                latest_state,
                latest_choices,
                generator=generator,
                policy=policy,
            )
        except ValueError as error:
            print("Execution guard -> BLOCKED")
            print(f"Reason -> current D9 recommendation unavailable: {error}")
            print("Injected bridge command sent -> False")
            print("Gameplay action executed -> False")
            print("Mouse input sent -> False")
            print("Observation process writes -> False")
            print("Hidden RNG/deck traversal -> False")
            return 0

        if _recommendation_signature(latest_view) != _recommendation_signature(view):
            print("Execution guard -> BLOCKED")
            print(
                "Reason -> top D9 recommendation or resolved B6 targets changed "
                "before dispatch; re-run from the new checkpoint"
            )
            print("Injected bridge command sent -> False")
            print("Gameplay action executed -> False")
            print("Mouse input sent -> False")
            print("Observation process writes -> False")
            print("Hidden RNG/deck traversal -> False")
            return 0

        bridge = FirstPartyBalatroBridge()
        try:
            bridge.ping()
        except InjectedBridgeError as error:
            print("Execution guard -> BLOCKED")
            print(f"Reason -> injected bridge unavailable: {error}")
            print("Injected bridge command sent -> False")
            print("Gameplay action executed -> False")
            print("Mouse input sent -> False")
            print("Observation process writes -> False")
            print("Hidden RNG/deck traversal -> False")
            return 0

        action = latest_view.recommendation.score.action
        print("Execution guard -> PASS")
        print("D9 recommendation unchanged -> True")
        print(
            "WARNING -> --execute is armed: exactly one real in-process D9 "
            "pack action will now be invoked"
        )
        print(f"Execution scope -> exactly one {action.name} action")
        if action.cards:
            print(
                "Armed B6 target indices -> "
                f"{_selected_card_indices(latest_state, action)}"
            )
        print("Mouse input sent -> False")

        try:
            result = LiveMemoryInjectedActionDispatcher(
                observer,
                bridge=bridge,
            ).dispatch(
                action,
                state=latest_state,
                snapshot=latest_snapshot,
            )
        except (InjectedBridgeError, RuntimeError) as error:
            print("Injected execution -> FAILED")
            print(f"Reason -> {error}")
            print("Follow-up action executed -> False")
            return 1

        print("Injected bridge command sent -> True")
        print(f"Checkpoint sequence -> {result.after.sequence}")
        print(f"Phase after -> {result.after.phase}")
        print("Follow-up action executed -> False")
        print("Observation process writes -> False")
        print("Hidden RNG/deck traversal -> False")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
