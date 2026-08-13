from __future__ import annotations

import argparse
from dataclasses import dataclass, fields

from games.balatro.actions import USE_CONSUMABLE, BalatroAction
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge, InjectedBridgeError
from games.balatro.live.injected.hand_dispatcher import LiveMemoryInjectedHandDispatcher
from games.balatro.live.planet_policy import HOLD, USE, LivePlanetPolicy, PlanetDecision, PlanetPolicyThresholds
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState

from .live_memory_observer import LiveMemoryBalatroObserver


@dataclass(frozen=True)
class LiveD7PlanetCandidate:
    planet: object
    label: str
    inventory_index: int
    decision: PlanetDecision


@dataclass(frozen=True)
class LiveD7PlanetView:
    snapshot: LiveBalatroSnapshot
    state: BalatroState
    thresholds: PlanetPolicyThresholds
    candidates: tuple[LiveD7PlanetCandidate, ...]
    recommendation: LiveD7PlanetCandidate | None


def _label(planet: object) -> str:
    return str(getattr(planet, "name", type(planet).__name__))


def evaluate_held_planets(
    state: BalatroState,
    policy: LivePlanetPolicy,
) -> tuple[LiveD7PlanetCandidate, ...]:
    candidates: list[LiveD7PlanetCandidate] = []
    for index, planet in enumerate(getattr(state, "consumables", ())):
        if str(getattr(planet, "category", "")).upper() != "PLANET":
            continue
        candidates.append(
            LiveD7PlanetCandidate(
                planet=planet,
                label=_label(planet),
                inventory_index=index,
                decision=policy.recommend(state, planet),
            )
        )
    return tuple(candidates)


def select_planet_recommendation(
    candidates: tuple[LiveD7PlanetCandidate, ...] | list[LiveD7PlanetCandidate],
) -> LiveD7PlanetCandidate | None:
    actionable = [candidate for candidate in candidates if candidate.decision.should_use]
    if not actionable:
        return None
    return max(
        actionable,
        key=lambda candidate: (
            float(candidate.decision.clear_probability_gain),
            float(candidate.decision.immediate_score_gain),
            int(candidate.decision.observed_hand_plays),
            int(candidate.decision.level_gain),
            -candidate.inventory_index,
            candidate.label,
        ),
    )


def build_live_d7_view(
    snapshot: LiveBalatroSnapshot,
    state: BalatroState,
    *,
    policy: LivePlanetPolicy | None = None,
) -> LiveD7PlanetView:
    if state.phase != "SELECTING_HAND":
        raise ValueError(
            f"D7 live validator requires SELECTING_HAND phase, observed {state.phase}"
        )
    active_policy = policy or LivePlanetPolicy()
    candidates = evaluate_held_planets(state, active_policy)
    return LiveD7PlanetView(
        snapshot=snapshot,
        state=state,
        thresholds=active_policy.thresholds,
        candidates=candidates,
        recommendation=select_planet_recommendation(candidates),
    )


def _state_fingerprint(state: BalatroState) -> tuple:
    def card_signature(card: object) -> tuple:
        return (
            getattr(card, "live_id", None),
            str(getattr(card, "rank", "")),
            str(getattr(card, "suit", "")),
            getattr(card, "enhancement", None),
            getattr(card, "edition", None),
            getattr(card, "seal", None),
        )

    def consumable_signature(item: object) -> tuple:
        return (
            getattr(item, "live_id", None),
            str(getattr(item, "name", "")),
            str(getattr(item, "category", "")),
            str(getattr(item, "hand_type", "")),
        )

    def joker_signature(joker: object) -> tuple:
        return (
            getattr(joker, "live_id", None),
            type(joker).__name__,
            getattr(joker, "edition", None),
        )

    blind_requirement = int(getattr(getattr(state, "blind", None), "requirement", 0))
    return (
        state.phase,
        int(getattr(state, "score", 0)),
        int(getattr(state, "hands_remaining", 0)),
        int(getattr(state, "consumable_slots", 0)),
        blind_requirement,
        tuple(card_signature(card) for card in getattr(state, "hand", ())),
        tuple(consumable_signature(item) for item in getattr(state, "consumables", ())),
        tuple(joker_signature(joker) for joker in getattr(state, "jokers", ())),
        tuple(sorted((getattr(state, "hand_levels", {}) or {}).items())),
        tuple(sorted((getattr(state, "hand_play_counts", {}) or {}).items())),
    )


def _execution_guard_errors(
    view: LiveD7PlanetView,
    *,
    expect_planet: str,
    expect_index: int,
    expect_decision: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    if expect_decision != USE:
        errors.append("armed D7 validation only executes an expected USE decision")

    matching = [
        candidate
        for candidate in view.candidates
        if candidate.inventory_index == expect_index
    ]
    if len(matching) != 1:
        errors.append(f"expected Planet inventory index {expect_index} is not present")
        return tuple(errors)

    candidate = matching[0]
    if candidate.label != expect_planet:
        errors.append(
            f"expected Planet {expect_planet!r} at index {expect_index}, observed {candidate.label!r}"
        )
    if candidate.decision.decision != expect_decision:
        errors.append(
            f"expected decision {expect_decision}, observed {candidate.decision.decision}"
        )
    if view.recommendation is None:
        errors.append("D7 currently recommends HOLD across all held Planets")
    elif view.recommendation.inventory_index != expect_index:
        errors.append(
            "expected Planet is not the current top D7 USE recommendation; "
            f"recommended index is {view.recommendation.inventory_index}"
        )
    return tuple(errors)


def _print_thresholds(thresholds: PlanetPolicyThresholds) -> None:
    print("D7 thresholds:")
    for field in fields(thresholds):
        print(f"  {field.name}={getattr(thresholds, field.name)}")


def _print_candidate(candidate: LiveD7PlanetCandidate) -> None:
    decision = candidate.decision
    print(
        f"Planet slot={candidate.inventory_index} -> {candidate.label!r} "
        f"hand={getattr(candidate.planet, 'hand_type', 'unknown')} "
        f"decision={decision.decision}"
    )
    print(f"  level_gain={decision.level_gain}")
    print(f"  observed_hand_plays={decision.observed_hand_plays}")
    print(f"  immediate_score_gain={decision.immediate_score_gain:.3f}")
    print(f"  clear_probability_gain={decision.clear_probability_gain:.6f}")
    print(f"  duplicate_hold_value={decision.duplicate_hold_value:.3f}")
    for note in decision.rationale:
        print(f"  note: {note}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "D7 Planet policy validation against the repository-owned live-memory "
            "observer. Preview mode is read-only. --execute submits exactly one "
            "validated held-Planet USE through the first-party injected bridge."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expect-planet")
    parser.add_argument("--expect-index", type=int)
    parser.add_argument("--expect-decision", choices=(USE, HOLD))
    args = parser.parse_args()

    expectations = (args.expect_planet, args.expect_index, args.expect_decision)
    if args.execute and any(value is None for value in expectations):
        parser.error(
            "--execute requires --expect-planet, --expect-index and --expect-decision USE"
        )
    if args.execute and args.expect_decision != USE:
        parser.error("--execute requires --expect-decision USE")
    if not args.execute and any(value is not None for value in expectations):
        parser.error("execution expectations are only valid with --execute")
    if args.expect_index is not None and args.expect_index < 0:
        parser.error("--expect-index must be non-negative")

    translator = DefaultBalatroStateTranslator()
    policy = LivePlanetPolicy()

    with LiveMemoryBalatroObserver() as observer:
        snapshot = observer.observe()
        state = translator.translate(snapshot)
        try:
            view = build_live_d7_view(snapshot, state, policy=policy)
        except ValueError as error:
            parser.error(str(error))

        print("Live-memory D7 Planet policy validation -> READY")
        print("Observation source -> live Balatro process memory")
        print("Execution backend -> game-ai-framework injected Lua bridge")
        print("Mouse input required -> False")
        print(f"Deck / stake -> {state.deck_name} / {state.stake_name}")
        print(f"Held Planets -> {len(view.candidates)}")
        _print_thresholds(view.thresholds)
        for candidate in view.candidates:
            _print_candidate(candidate)

        if view.recommendation is None:
            print("Recommended D7 action -> HOLD")
        else:
            recommendation = view.recommendation
            print(
                f"Recommended D7 action -> USE slot={recommendation.inventory_index} "
                f"{recommendation.label!r}"
            )

        if not args.execute:
            print("Execution guard -> PREVIEW ONLY")
            print("Injected bridge command sent -> False")
            print("Gameplay action executed -> False")
            print("Mouse input sent -> False")
            print("Observation process writes -> False")
            return 0

        assert args.expect_planet is not None
        assert args.expect_index is not None
        assert args.expect_decision is not None
        guard_errors = _execution_guard_errors(
            view,
            expect_planet=args.expect_planet,
            expect_index=args.expect_index,
            expect_decision=args.expect_decision,
        )
        if guard_errors:
            print("Execution guard -> BLOCKED")
            for error in guard_errors:
                print(f"Reason -> {error}")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        latest_snapshot = observer.observe()
        latest_state = translator.translate(latest_snapshot)
        if (
            latest_snapshot.sequence != snapshot.sequence
            or _state_fingerprint(latest_state) != _state_fingerprint(state)
        ):
            print("Execution guard -> BLOCKED")
            print("Reason -> live D7 state changed during planning; re-run from the new checkpoint")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        latest_view = build_live_d7_view(latest_snapshot, latest_state, policy=policy)
        latest_errors = _execution_guard_errors(
            latest_view,
            expect_planet=args.expect_planet,
            expect_index=args.expect_index,
            expect_decision=args.expect_decision,
        )
        if latest_errors:
            print("Execution guard -> BLOCKED")
            for error in latest_errors:
                print(f"Reason -> {error}")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        candidate = next(
            candidate
            for candidate in latest_view.candidates
            if candidate.inventory_index == args.expect_index
        )
        action = BalatroAction(USE_CONSUMABLE, target=candidate.planet)
        bridge = FirstPartyBalatroBridge()
        try:
            bridge.ping()
        except InjectedBridgeError as error:
            print("Execution guard -> BLOCKED")
            print(f"Reason -> first-party injected bridge unavailable: {error}")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        print("Execution guard -> PASS")
        print("Execution scope -> exactly one D7 held-Planet USE")
        print("Mouse input sent -> False")
        try:
            result = LiveMemoryInjectedHandDispatcher(observer, bridge=bridge).dispatch(
                action,
                state=latest_state,
                snapshot=latest_snapshot,
            )
        except (InjectedBridgeError, RuntimeError) as error:
            print("Injected execution -> FAILED")
            print(f"Reason -> {error}")
            return 1

        after_state = translator.translate(result.after)
        hand_type = str(getattr(candidate.planet, "hand_type", ""))
        print("Injected bridge command sent -> True")
        print(f"Executed Planet -> {candidate.label!r}")
        print(f"Checkpoint sequence -> {result.after.sequence}")
        print(f"Phase after -> {after_state.phase}")
        print(
            f"Hand level after -> {hand_type}="
            f"{after_state.hand_levels.get(hand_type)}"
        )
        print("Follow-up gameplay action executed -> False")
        print("Observation process writes -> False")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
