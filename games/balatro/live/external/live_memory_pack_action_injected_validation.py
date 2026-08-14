from __future__ import annotations

import argparse

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.injected import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.pack_policy import BalatroPackPolicy

from .live_memory_observer import LiveMemoryBalatroObserver


_ACTIONS = (SELECT_PACK_CARD, SKIP_BOOSTER)


def _label(choice: LivePackChoice) -> str:
    return str(choice.label or "<unknown>")


def _center(choice: LivePackChoice) -> str:
    return str(choice.data.get("center") or "<unknown>")


def _choice_signature(choices: list[LivePackChoice] | tuple[LivePackChoice, ...]) -> tuple[tuple, ...]:
    return tuple(
        (
            int(choice.area_index),
            choice.live_id,
            _label(choice),
            choice.kind,
            _center(choice),
        )
        for choice in choices
    )


def _choice_at(choices, index: int) -> LivePackChoice | None:
    return next(
        (choice for choice in choices if int(choice.area_index) == int(index)),
        None,
    )


def _ranked_select_action(ranked, index: int) -> BalatroAction | None:
    """Return the policy-produced semantic action for one visible pack choice.

    Pack policy may attach B6-selected hand targets to SELECT_PACK_CARD. Armed
    validation must execute that exact semantic action rather than reconstructing a
    bare selection and silently discarding the target plan.
    """
    for scored in ranked:
        action = scored.action
        if action.name != SELECT_PACK_CARD:
            continue
        target = action.target
        if isinstance(target, LivePackChoice) and int(target.area_index) == int(index):
            return action
    return None


def _guard_errors(
    *,
    phase: str,
    state_complete: bool,
    choices,
    action_name: str,
    expected_phase: str,
    index: int | None = None,
    expected_label: str | None = None,
    expected_center: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not phase.endswith("_PACK"):
        errors.append(f"expected a *_PACK phase, observed {phase}")
    if phase != expected_phase:
        errors.append(f"expected phase {expected_phase}, observed {phase}")
    if not state_complete:
        errors.append(f"{phase} is not complete")

    if action_name == SKIP_BOOSTER:
        return errors
    if action_name != SELECT_PACK_CARD:
        errors.append(f"unsupported pack action {action_name}")
        return errors

    if index is None:
        errors.append("SELECT_PACK_CARD has no target index")
        return errors
    if index < 0:
        errors.append("pack target index cannot be negative")
        return errors

    choice = _choice_at(choices, index)
    if choice is None:
        errors.append(f"pack choice index {index} is not currently visible")
        return errors

    observed_label = _label(choice)
    observed_center = _center(choice)
    if expected_label is None:
        errors.append("SELECT_PACK_CARD has no expected label")
    elif observed_label != expected_label:
        errors.append(
            f"expected label {expected_label!r}, observed {observed_label!r}"
        )
    if expected_center is None:
        errors.append("SELECT_PACK_CARD has no expected center")
    elif observed_center != expected_center:
        errors.append(
            f"expected center {expected_center!r}, observed {observed_center!r}"
        )
    return errors


def _action_text(action: BalatroAction) -> str:
    if action.name == SKIP_BOOSTER:
        return SKIP_BOOSTER
    choice = action.target
    target_text = ""
    if action.cards:
        target_text = f", hand_targets={len(action.cards)}"
    return (
        f"{SELECT_PACK_CARD}: index={choice.area_index}, "
        f"label={_label(choice)!r}, center={_center(choice)!r}{target_text}"
    )


def _print_choices(choices) -> None:
    print(f"Visible pack choices -> {len(choices)}")
    for choice in choices:
        value = choice.data.get("value") or {}
        card_text = ""
        if value.get("rank") is not None or value.get("suit") is not None:
            card_text = f" | card={value.get('rank')}/{value.get('suit')}"
        print(
            f"  {choice.area_index}: {_label(choice)} | set={choice.kind} | "
            f"center={_center(choice)}{card_text}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Guarded first-party injected validation for visible Balatro booster-pack "
            "actions. Preview mode is read-only. --execute invokes exactly one pack "
            "selection or Skip action through the repo-owned bridge and sends no mouse input."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--action", choices=_ACTIONS)
    parser.add_argument("--expect-phase")
    parser.add_argument("--index", type=int)
    parser.add_argument("--expect-label")
    parser.add_argument("--expect-center")
    args = parser.parse_args()

    select_fields = (args.index, args.expect_label, args.expect_center)
    if args.execute:
        if args.action is None or args.expect_phase is None:
            parser.error("--execute requires --action and --expect-phase")
        if args.action == SELECT_PACK_CARD:
            if any(value is None for value in select_fields):
                parser.error(
                    "SELECT_PACK_CARD execution requires --index, --expect-label, "
                    "and --expect-center"
                )
        elif any(value is not None for value in select_fields):
            parser.error(
                "SKIP_BOOSTER does not accept --index, --expect-label, or --expect-center"
            )
    elif any(
        value is not None
        for value in (
            args.action,
            args.expect_phase,
            args.index,
            args.expect_label,
            args.expect_center,
        )
    ):
        parser.error("execution expectations are only valid with --execute")

    with LiveMemoryBalatroObserver() as observer:
        snapshot = observer.observe()
        if not snapshot.phase.endswith("_PACK"):
            parser.error(
                f"pack injected validation requires a *_PACK phase, observed {snapshot.phase}"
            )
        if not snapshot.state_complete:
            parser.error(f"{snapshot.phase} is not complete; wait for the UI to settle")

        generator = LivePackActionGenerator()
        translator = DefaultBalatroStateTranslator()
        policy = BalatroPackPolicy()
        choices = generator.read_choices(observer)
        state = translator.translate(snapshot)
        actions = generator.generate_actions(state, list(choices))
        ranked = policy.rank_actions(state, actions)

        print("Live-memory first-party injected pack validation -> READY")
        print("Observation source -> live Balatro process memory")
        print("Execution backend -> game-ai-framework injected Lua bridge")
        print("Runtime loader -> none (fused LÖVE archive)")
        print("Lovely required -> False")
        print("Steamodded required -> False")
        print("BalatroBot required -> False")
        print("Mouse calibration required -> False")
        print(f"Phase -> {snapshot.phase}")
        _print_choices(choices)
        print(f"Available pack actions -> {len(actions)}")
        for action in actions:
            print("  " + _action_text(action))
        if ranked:
            print(f"Recommended pack action -> {_action_text(ranked[0].action)}")
        print("Observation process writes -> False")
        print("Hidden RNG/deck traversal -> False")

        if not args.execute:
            print("Execution guard -> PREVIEW ONLY")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        assert args.action is not None
        assert args.expect_phase is not None
        errors = _guard_errors(
            phase=snapshot.phase,
            state_complete=snapshot.state_complete,
            choices=choices,
            action_name=args.action,
            expected_phase=args.expect_phase,
            index=args.index,
            expected_label=args.expect_label,
            expected_center=args.expect_center,
        )
        if errors:
            print("Execution guard -> BLOCKED")
            for error in errors:
                print(f"Reason -> {error}")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        latest = observer.observe()
        latest_choices = generator.read_choices(observer)
        if (
            latest.phase != snapshot.phase
            or not latest.state_complete
            or _choice_signature(latest_choices) != _choice_signature(choices)
        ):
            print("Execution guard -> BLOCKED")
            print(
                "Reason -> live booster-pack state changed before dispatch; "
                "re-run from the new checkpoint"
            )
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        # Rebuild the policy decision from the final guarded checkpoint. Targeted
        # Tarot/Spectral actions carry Card objects from this translated state, and
        # the injected dispatcher requires this exact state to map them to native
        # hand indices and verify their semantic postcondition.
        latest_state = translator.translate(latest)
        latest_actions = generator.generate_actions(latest_state, list(latest_choices))
        latest_ranked = policy.rank_actions(latest_state, latest_actions)

        bridge = FirstPartyBalatroBridge()
        try:
            bridge.ping()
        except InjectedBridgeError as error:
            print("Execution guard -> BLOCKED")
            print(f"Reason -> injected bridge unavailable: {error}")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        if args.action == SELECT_PACK_CARD:
            assert args.index is not None
            action = _ranked_select_action(latest_ranked, args.index)
            if action is None:
                print("Execution guard -> BLOCKED")
                print(
                    "Reason -> guarded visible choice has no policy-produced semantic action"
                )
                print("Injected bridge command sent -> False")
                print("Mouse input sent -> False")
                return 0
            target = action.target
        else:
            target = None
            action = BalatroAction(SKIP_BOOSTER)

        print("Execution guard -> PASS")
        print(
            "WARNING -> --execute is armed: one real in-process Balatro "
            "booster-pack action will now be invoked"
        )
        print(f"Execution scope -> exactly one {args.action} action")
        if target is not None:
            print(
                f"Armed target -> index={target.area_index} "
                f"label={_label(target)!r} center={_center(target)!r}"
            )
            if action.cards:
                print(f"Policy-selected hand targets -> {len(action.cards)}")
        print("Mouse input sent -> False")

        try:
            result = LiveMemoryInjectedActionDispatcher(
                observer,
                bridge=bridge,
            ).dispatch(action, state=latest_state, snapshot=latest)
        except (InjectedBridgeError, RuntimeError) as error:
            print("Injected execution -> FAILED")
            print(f"Reason -> {error}")
            print("Follow-up action executed -> False")
            return 1

        print("Injected bridge command sent -> True")
        print(f"Checkpoint sequence -> {result.after.sequence}")
        print(f"Phase after -> {result.after.phase}")
        print("Follow-up action executed -> False")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
