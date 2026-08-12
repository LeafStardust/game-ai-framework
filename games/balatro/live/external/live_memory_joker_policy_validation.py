from __future__ import annotations

from dataclasses import dataclass

from games.balatro.joker_policy import (
    BUY,
    HOLD,
    REPLACE,
    JokerAcquisitionDecision,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.state import BalatroState

from .live_memory_observer import LiveMemoryBalatroObserver


@dataclass(frozen=True)
class LiveD2JokerCandidate:
    target: object
    label: str
    area_index: int | None
    decision: JokerAcquisitionDecision
    transition: object

    @property
    def selected_advantage(self) -> float | None:
        selected = self.decision.selected
        return None if selected is None else float(selected.total_advantage)


@dataclass(frozen=True)
class LiveD2JokerView:
    snapshot: LiveBalatroSnapshot
    state: BalatroState
    playbook_name: str
    playbook_version: str
    thresholds: JokerAcquisitionThresholds
    candidates: tuple[LiveD2JokerCandidate, ...]
    recommendation: LiveD2JokerCandidate | None


def _label(target: object) -> str:
    return str(
        getattr(
            target,
            "label",
            getattr(target, "name", type(target).__name__),
        )
    )


def _area_index(target: object) -> int | None:
    value = getattr(target, "area_index", None)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def evaluate_shop_jokers(
    state: BalatroState,
    policy: JokerAcquisitionPolicy,
) -> tuple[LiveD2JokerCandidate, ...]:
    """Evaluate every visible shop Joker, including full-slot replacements.

    This intentionally does not use ``BalatroShopActionGenerator``. That generator
    correctly suppresses executable BUY_JOKER actions when the Joker bar is full,
    while D2 still needs to reason about those visible Jokers as replacement
    candidates before sell/replace execution is enabled.
    """

    candidates: list[LiveD2JokerCandidate] = []
    for target in getattr(state, "shop_jokers", ()):
        transition = policy.transition_planner.plan(state, target)
        decision = policy.decide(state, target)
        candidates.append(
            LiveD2JokerCandidate(
                target=target,
                label=_label(target),
                area_index=_area_index(target),
                decision=decision,
                transition=transition,
            )
        )
    return tuple(candidates)


def select_joker_recommendation(
    candidates: tuple[LiveD2JokerCandidate, ...] | list[LiveD2JokerCandidate],
) -> LiveD2JokerCandidate | None:
    actionable = [
        candidate
        for candidate in candidates
        if candidate.decision.action in {BUY, REPLACE}
        and candidate.decision.selected is not None
    ]
    if not actionable:
        return None
    return max(
        actionable,
        key=lambda candidate: (
            float(candidate.decision.selected.total_advantage),
            -(candidate.area_index if candidate.area_index is not None else 10**9),
            candidate.label,
        ),
    )


def build_live_d2_view(
    snapshot: LiveBalatroSnapshot,
    state: BalatroState,
) -> LiveD2JokerView:
    if state.phase != "SHOP":
        raise ValueError(f"D2 live validator requires SHOP phase, observed {state.phase}")

    playbook = default_balatro_playbooks().for_state(state)
    thresholds = JokerAcquisitionThresholds.from_mapping(
        playbook.strategy.get("decision_thresholds", {}).get(
            "joker_acquisition",
            {},
        )
    )
    policy = JokerAcquisitionPolicy(thresholds)
    candidates = evaluate_shop_jokers(state, policy)
    return LiveD2JokerView(
        snapshot=snapshot,
        state=state,
        playbook_name=playbook.name,
        playbook_version=playbook.version,
        thresholds=thresholds,
        candidates=candidates,
        recommendation=select_joker_recommendation(candidates),
    )


def _price(target: object) -> int:
    value = getattr(target, "price", getattr(target, "cost", 0))
    if isinstance(value, dict):
        value = value.get("buy", 0)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _print_thresholds(thresholds: JokerAcquisitionThresholds) -> None:
    print("D2 thresholds:")
    for name, value in thresholds.as_dict().items():
        print(f"  {name}={value}")


def _print_candidate(index: int, candidate: LiveD2JokerCandidate) -> None:
    target = candidate.target
    decision = candidate.decision
    transition = candidate.transition
    build_value = transition.candidate_value
    edition = getattr(target, "edition", None)

    print(
        f"Candidate {index} -> {candidate.label!r} "
        f"slot={candidate.area_index} price=${_price(target)} "
        f"modeled={build_value.joker != type(target).__name__ or build_value.total_gain != 0.0 or not build_value.rationale == ('candidate is not a modeled Joker',)}"
    )
    if edition:
        print(f"  edition={edition}")
    print(f"  recommendation={decision.action}")
    print(f"  whole_build_gain={build_value.total_gain:.3f}")
    print(f"  representative_scoring_gain={build_value.direct_scoring_gain:.6f}")
    print(f"  B3_intrinsic={build_value.contextual.intrinsic_gain:.3f}")
    print(f"  B3_interaction={build_value.contextual.interaction_gain:.3f}")

    for note in build_value.rationale:
        print(f"  build_note: {note}")

    if not decision.options:
        for note in decision.rationale:
            print(f"  decision_note: {note}")
        return

    print(f"  transaction_options={len(decision.options)}")
    for option_index, option in enumerate(decision.options, start=1):
        economics = option.economics
        replacement = ""
        if option.mode == REPLACE:
            replacement = (
                f" replace_slot={option.replace_index} "
                f"replace={option.replace_joker}"
            )
        print(
            f"    {option_index}. mode={option.mode}{replacement} "
            f"eligible={option.eligible} build_gain={option.build_gain:.3f} "
            f"advantage={option.total_advantage:.3f}"
        )
        print(
            "       economics: "
            f"price=${economics.price} sell_credit=${economics.sell_credit} "
            f"net_spend=${economics.net_spend} money_after=${economics.money_after} "
            f"edition_delta={economics.edition_delta:.3f} "
            f"price_penalty={economics.price_penalty:.3f} "
            f"interest_penalty={economics.interest_penalty:.3f} "
            f"reserve_penalty={economics.reserve_penalty:.3f} "
            f"slot_penalty={economics.slot_penalty:.3f}"
        )
        for note in option.rationale:
            print(f"       note: {note}")

    for note in decision.rationale:
        print(f"  decision_note: {note}")


def main() -> int:
    try:
        with LiveMemoryBalatroObserver() as observer:
            snapshot = observer.observe()
            state = DefaultBalatroStateTranslator().translate(snapshot)
            view = build_live_d2_view(snapshot, state)
    except Exception as error:
        print("Live-memory D2 Joker policy -> FAIL")
        print(f"Reason -> {error}")
        print("Gameplay action executed -> False")
        print("Achievement status command sent -> False")
        print("Mouse input sent -> False")
        print("Observation process writes -> False")
        return 2

    print("Live-memory D2 Joker policy -> READY")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {view.state.phase}")
    print(f"Deck / Stake -> {view.state.deck_name} / {view.state.stake_name}")
    print(f"Playbook -> {view.playbook_name} v{view.playbook_version}")
    print(f"Money -> ${view.state.money}")
    print(f"Joker slots -> {len(view.state.jokers)}/{view.state.joker_slots}")
    print(f"Visible shop Jokers -> {len(view.candidates)}")
    _print_thresholds(view.thresholds)

    for index, candidate in enumerate(view.candidates, start=1):
        _print_candidate(index, candidate)

    recommendation = view.recommendation
    if recommendation is None:
        print("Recommended D2 action -> HOLD")
    else:
        selected = recommendation.decision.selected
        assert selected is not None
        print(
            f"Recommended D2 action -> {recommendation.decision.action} "
            f"{recommendation.label!r} advantage={selected.total_advantage:.3f}"
        )
        if recommendation.decision.action == REPLACE:
            print(
                "Recommended replacement -> "
                f"slot={selected.replace_index} {selected.replace_joker}"
            )

    print("Live replacement execution available -> False")
    print("Gameplay action executed -> False")
    print("Achievement status command sent -> False")
    print("Mouse input sent -> False")
    print("Observation process writes -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
