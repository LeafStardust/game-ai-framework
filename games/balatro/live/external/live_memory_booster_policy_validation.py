from __future__ import annotations

import argparse
from dataclasses import dataclass, fields

from games.balatro.actions import BUY_BOOSTER, BalatroAction
from games.balatro.live.injected import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.shop_booster_policy import (
    BUY,
    HOLD,
    BoosterAcquisitionThresholds,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
)
from games.balatro.state import BalatroState

from .live_memory_observer import LiveMemoryBalatroObserver


@dataclass(frozen=True)
class LiveD8BoosterCandidate:
    booster: object
    label: str
    area_index: int
    recommendation: ShopBoosterRecommendation


@dataclass(frozen=True)
class LiveD8BoosterView:
    snapshot: LiveBalatroSnapshot
    state: BalatroState
    thresholds: BoosterAcquisitionThresholds
    candidates: tuple[LiveD8BoosterCandidate, ...]
    recommendation: LiveD8BoosterCandidate | None


def _label(booster: object) -> str:
    return str(getattr(booster, "label", type(booster).__name__))


def policy_for_state(state: BalatroState) -> BuildAwareShopBoosterPolicy:
    try:
        playbook = default_balatro_playbooks().for_state(state)
    except BalatroPlaybookNotFound:
        return BuildAwareShopBoosterPolicy()
    thresholds = BoosterAcquisitionThresholds.from_mapping(
        playbook.strategy.get("decision_thresholds", {}).get(
            "booster_acquisition",
            {},
        )
    )
    return BuildAwareShopBoosterPolicy(thresholds=thresholds)


def evaluate_shop_boosters(
    state: BalatroState,
    policy: BuildAwareShopBoosterPolicy,
) -> tuple[LiveD8BoosterCandidate, ...]:
    candidates: list[LiveD8BoosterCandidate] = []
    for fallback_index, booster in enumerate(getattr(state, "shop_boosters", ())):
        raw_index = getattr(booster, "area_index", None)
        area_index = fallback_index if raw_index is None else int(raw_index)
        action = BalatroAction(BUY_BOOSTER, target=booster)
        candidates.append(
            LiveD8BoosterCandidate(
                booster=booster,
                label=_label(booster),
                area_index=area_index,
                recommendation=policy.recommend(state, action),
            )
        )
    return tuple(candidates)


def select_booster_recommendation(
    candidates: tuple[LiveD8BoosterCandidate, ...] | list[LiveD8BoosterCandidate],
) -> LiveD8BoosterCandidate | None:
    actionable = [
        candidate
        for candidate in candidates
        if candidate.recommendation.decision == BUY
    ]
    if not actionable:
        return None
    return max(
        actionable,
        key=lambda candidate: (
            float(candidate.recommendation.advantage_over_save),
            float(candidate.recommendation.at_least_one_hit_probability),
            float(candidate.recommendation.option_utility),
            -candidate.area_index,
            candidate.label,
        ),
    )


def build_live_d8_view(
    snapshot: LiveBalatroSnapshot,
    state: BalatroState,
    *,
    policy: BuildAwareShopBoosterPolicy | None = None,
) -> LiveD8BoosterView:
    if state.phase != "SHOP":
        raise ValueError(
            f"D8 live validator requires SHOP phase, observed {state.phase}"
        )
    active_policy = policy or policy_for_state(state)
    candidates = evaluate_shop_boosters(state, active_policy)
    return LiveD8BoosterView(
        snapshot=snapshot,
        state=state,
        thresholds=active_policy.thresholds,
        candidates=candidates,
        recommendation=select_booster_recommendation(candidates),
    )


def _state_fingerprint(state: BalatroState) -> tuple:
    def card_signature(card: object) -> tuple:
        return (
            str(getattr(card, "rank", "")),
            str(getattr(card, "suit", "")),
            str(getattr(card, "enhancement", "") or ""),
            str(getattr(card, "edition", "") or ""),
            str(getattr(card, "seal", "") or ""),
        )

    def joker_signature(joker: object) -> tuple:
        return (
            str(getattr(joker, "live_id", "") or ""),
            type(joker).__name__,
            str(getattr(joker, "edition", "") or ""),
        )

    def consumable_signature(item: object) -> tuple:
        return (
            str(getattr(item, "live_id", "") or ""),
            str(getattr(item, "name", "")),
            str(getattr(item, "category", "")),
        )

    def booster_signature(item: object) -> tuple:
        raw_index = getattr(item, "area_index", None)
        return (
            str(getattr(item, "live_id", "") or ""),
            str(getattr(item, "label", "")),
            int(getattr(item, "price", 0)),
            -1 if raw_index is None else int(raw_index),
            str(getattr(item, "center", "") or ""),
        )

    owned_deck = getattr(state, "owned_deck", None)
    deck = owned_deck if owned_deck is not None else getattr(state, "deck", ())
    return (
        state.phase,
        int(getattr(state, "money", 0)),
        int(getattr(state, "ante", 0)),
        int(getattr(state, "joker_slots", 0)),
        int(getattr(state, "consumable_slots", 0)),
        tuple(sorted(card_signature(card) for card in deck)),
        tuple(joker_signature(joker) for joker in getattr(state, "jokers", ())),
        tuple(
            consumable_signature(item)
            for item in getattr(state, "consumables", ())
        ),
        tuple(
            booster_signature(item)
            for item in getattr(state, "shop_boosters", ())
        ),
        tuple(sorted((getattr(state, "hand_levels", {}) or {}).items())),
        tuple(sorted((getattr(state, "hand_play_counts", {}) or {}).items())),
    )


def _execution_guard_errors(
    view: LiveD8BoosterView,
    *,
    expect_booster: str,
    expect_index: int,
    expect_decision: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    if expect_decision != BUY:
        errors.append("armed D8 validation only executes an expected BUY decision")

    matching = [
        candidate
        for candidate in view.candidates
        if candidate.area_index == expect_index
    ]
    if len(matching) != 1:
        errors.append(f"expected booster area index {expect_index} is not present")
        return tuple(errors)

    candidate = matching[0]
    if candidate.label != expect_booster:
        errors.append(
            f"expected booster {expect_booster!r} at index {expect_index}, "
            f"observed {candidate.label!r}"
        )
    if candidate.recommendation.decision != expect_decision:
        errors.append(
            f"expected decision {expect_decision}, observed "
            f"{candidate.recommendation.decision}"
        )
    if view.recommendation is None:
        errors.append("D8 currently recommends SAVE/HOLD across all visible boosters")
    elif view.recommendation.area_index != expect_index:
        errors.append(
            "expected booster is not the current top D8 BUY recommendation; "
            f"recommended index is {view.recommendation.area_index}"
        )
    return tuple(errors)


def _print_thresholds(thresholds: BoosterAcquisitionThresholds) -> None:
    print("D8 thresholds:")
    for field in fields(thresholds):
        print(f"  {field.name}={getattr(thresholds, field.name)}")


def _print_candidate(candidate: LiveD8BoosterCandidate) -> None:
    recommendation = candidate.recommendation
    print(
        f"Booster index={candidate.area_index} -> {candidate.label!r} "
        f"family={recommendation.family} variant={recommendation.variant} "
        f"decision={recommendation.decision}"
    )
    print(f"  build_need_score={recommendation.build_need_score:.3f}")
    print(
        "  per_offer_hit_probability="
        f"{recommendation.per_offer_hit_probability:.3f}"
    )
    print(
        "  at_least_one_hit_probability="
        f"{recommendation.at_least_one_hit_probability:.3f}"
    )
    print(
        f"  offers={recommendation.offer_count} "
        f"selections={recommendation.selection_count}"
    )
    print(f"  option_utility={recommendation.option_utility:.3f}")
    print(
        f"  advantage_over_save={recommendation.advantage_over_save:.3f}"
    )
    print(f"  arbiter_scale_total={recommendation.total:.3f}")
    for note in recommendation.rationale:
        print(f"  note: {note}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "D8 Balatro booster-acquisition validation against the repository-owned "
            "live-memory observer. Preview mode is read-only. --execute submits "
            "exactly one validated in-game BUY_BOOSTER through the first-party "
            "injected bridge and stops before any pack choice."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expect-booster")
    parser.add_argument("--expect-index", type=int)
    parser.add_argument("--expect-decision", choices=(BUY, HOLD))
    args = parser.parse_args()

    expectations = (
        args.expect_booster,
        args.expect_index,
        args.expect_decision,
    )
    if args.execute and any(value is None for value in expectations):
        parser.error(
            "--execute requires --expect-booster, --expect-index and "
            "--expect-decision BUY"
        )
    if args.execute and args.expect_decision != BUY:
        parser.error("--execute requires --expect-decision BUY")
    if not args.execute and any(value is not None for value in expectations):
        parser.error("execution expectations are only valid with --execute")
    if args.expect_index is not None and args.expect_index < 0:
        parser.error("--expect-index must be non-negative")

    translator = DefaultBalatroStateTranslator()

    with LiveMemoryBalatroObserver() as observer:
        snapshot = observer.observe()
        state = translator.translate(snapshot)
        try:
            view = build_live_d8_view(snapshot, state)
        except ValueError as error:
            parser.error(str(error))

        print("Live-memory D8 booster policy validation -> READY")
        print("Observation source -> live Balatro process memory")
        print("Execution backend -> game-ai-framework injected Lua bridge")
        print("Mouse input required -> False")
        print(f"Deck / stake -> {state.deck_name} / {state.stake_name}")
        print(f"Money -> {state.money}")
        print(f"Visible boosters -> {len(view.candidates)}")
        _print_thresholds(view.thresholds)
        for candidate in view.candidates:
            _print_candidate(candidate)

        if view.recommendation is None:
            print("Recommended D8 action -> SAVE/HOLD")
        else:
            recommendation = view.recommendation
            print(
                f"Recommended D8 action -> BUY index={recommendation.area_index} "
                f"{recommendation.label!r}"
            )

        if not args.execute:
            print("Execution guard -> PREVIEW ONLY")
            print("Injected bridge command sent -> False")
            print("Gameplay action executed -> False")
            print("Mouse input sent -> False")
            print("Observation process writes -> False")
            return 0

        assert args.expect_booster is not None
        assert args.expect_index is not None
        assert args.expect_decision is not None
        guard_errors = _execution_guard_errors(
            view,
            expect_booster=args.expect_booster,
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
            print(
                "Reason -> live D8 state changed during planning; "
                "re-run from the new checkpoint"
            )
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        latest_view = build_live_d8_view(latest_snapshot, latest_state)
        latest_errors = _execution_guard_errors(
            latest_view,
            expect_booster=args.expect_booster,
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
            if candidate.area_index == args.expect_index
        )
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
        print("Execution scope -> exactly one D8 in-game booster BUY")
        print("Mouse input sent -> False")
        try:
            result = LiveMemoryInjectedActionDispatcher(
                observer,
                bridge=bridge,
            ).dispatch(
                BalatroAction(BUY_BOOSTER, target=candidate.booster),
                snapshot=latest_snapshot,
            )
        except (InjectedBridgeError, RuntimeError) as error:
            print("Injected execution -> FAILED")
            print(f"Reason -> {error}")
            return 1

        after_state = translator.translate(result.after)
        print("Injected bridge command sent -> True")
        print(f"Executed booster -> {candidate.label!r}")
        print(f"Checkpoint sequence -> {result.after.sequence}")
        print(f"Phase after -> {after_state.phase}")
        print(f"Money after -> {after_state.money}")
        print("Follow-up pack choice executed -> False")
        print("Mouse input sent -> False")
        print("Observation process writes -> False")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
