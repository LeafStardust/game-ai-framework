from __future__ import annotations

import argparse
import copy
import time
from dataclasses import dataclass

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.live.external.live_memory_observer import LiveMemoryBalatroObserver
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


DEFAULT_POLL_SECONDS = 0.10
EPSILON = 1e-9


@dataclass(frozen=True)
class DebuffedCardProbe:
    index: int
    live_id: int | str | None
    label: str
    hand_name: str
    actual_minimum: int
    actual_expected: float
    actual_maximum: int
    counterfactual_minimum: int
    counterfactual_expected: float
    counterfactual_maximum: int
    expected_suppressed: float
    structure_preserved: bool


@dataclass(frozen=True)
class BossDebuffValidation:
    applicable: bool
    passed: bool
    phase: str
    boss_name: str | None
    probes: tuple[DebuffedCardProbe, ...]
    reason: str


def _card_label(card) -> str:
    parts = [str(card.rank), str(card.suit)]
    if getattr(card, "enhancement", None):
        parts.append(str(card.enhancement))
    if getattr(card, "edition", None):
        parts.append(str(card.edition))
    if getattr(card, "seal", None):
        parts.append(str(card.seal))
    return " / ".join(parts)


def _single_card_projection(state, index: int, evaluator: LiveHandDecisionEvaluator):
    card = state.hand[index]
    return evaluator.project_play(
        state,
        BalatroAction(PLAY_CARDS, [card]),
    )


def analyze_boss_debuff_snapshot(
    snapshot: LiveBalatroSnapshot,
    *,
    translator: DefaultBalatroStateTranslator | None = None,
    evaluator: LiveHandDecisionEvaluator | None = None,
) -> BossDebuffValidation:
    """Validate debuff suppression against one authoritative public snapshot.

    The counterfactual changes only the translated public ``debuffed`` flag on one
    visible card. Rank, suit, modifiers, Jokers, hand levels and all other public
    state remain identical. The validator is therefore checking the production D1
    projection boundary rather than inventing a boss-specific scoring rule.
    """
    translator = translator or DefaultBalatroStateTranslator()
    evaluator = evaluator or LiveHandDecisionEvaluator()
    state = translator.translate(snapshot)
    boss_name = getattr(state, "boss_name", None)

    if str(state.phase) != "SELECTING_HAND":
        return BossDebuffValidation(
            applicable=False,
            passed=False,
            phase=str(state.phase),
            boss_name=boss_name,
            probes=(),
            reason="current checkpoint is not SELECTING_HAND",
        )

    if not boss_name:
        return BossDebuffValidation(
            applicable=False,
            passed=False,
            phase=str(state.phase),
            boss_name=None,
            probes=(),
            reason="current checkpoint is not an active Boss Blind hand",
        )

    debuffed_indices = [
        index
        for index, card in enumerate(state.hand)
        if bool(getattr(card, "debuffed", False))
    ]
    if not debuffed_indices:
        return BossDebuffValidation(
            applicable=False,
            passed=False,
            phase=str(state.phase),
            boss_name=str(boss_name),
            probes=(),
            reason="Boss Blind hand contains no currently debuffed visible cards",
        )

    probes: list[DebuffedCardProbe] = []
    for index in debuffed_indices:
        actual = _single_card_projection(state, index, evaluator)

        counterfactual_state = copy.deepcopy(state)
        counterfactual_state.hand[index].debuffed = False
        counterfactual = _single_card_projection(
            counterfactual_state,
            index,
            evaluator,
        )

        probes.append(
            DebuffedCardProbe(
                index=index,
                live_id=getattr(state.hand[index], "live_id", None),
                label=_card_label(state.hand[index]),
                hand_name=str(actual.hand.value),
                actual_minimum=int(actual.hand_score),
                actual_expected=float(actual.expected_hand_score),
                actual_maximum=int(actual.maximum_hand_score),
                counterfactual_minimum=int(counterfactual.hand_score),
                counterfactual_expected=float(counterfactual.expected_hand_score),
                counterfactual_maximum=int(counterfactual.maximum_hand_score),
                expected_suppressed=(
                    float(counterfactual.expected_hand_score)
                    - float(actual.expected_hand_score)
                ),
                structure_preserved=(actual.hand == counterfactual.hand),
            )
        )

    structure_preserved = all(probe.structure_preserved for probe in probes)
    suppression_observed = any(
        probe.expected_suppressed > EPSILON
        for probe in probes
    )
    passed = structure_preserved and suppression_observed

    if not structure_preserved:
        reason = "debuff flag changed poker-hand structure; expected structure preservation"
    elif not suppression_observed:
        reason = (
            "no positive D1 suppression delta was observable for the debuffed cards; "
            "checkpoint is inconclusive"
        )
    else:
        reason = (
            "live boss debuff reached D1: poker-hand structure stayed unchanged while "
            "the debuffed card's scoring/effect contribution was suppressed"
        )

    return BossDebuffValidation(
        applicable=True,
        passed=passed,
        phase=str(state.phase),
        boss_name=str(boss_name),
        probes=tuple(probes),
        reason=reason,
    )


def _print_validation(result: BossDebuffValidation) -> None:
    if not result.applicable:
        status = "NOT APPLICABLE"
    else:
        status = "PASS" if result.passed else "INCONCLUSIVE"

    print(f"Validation -> {status}")
    print(f"Phase -> {result.phase}")
    print(f"Boss -> {result.boss_name or '-'}")
    print(f"Read-only -> True")
    print(f"Reason -> {result.reason}")

    if not result.probes:
        return

    print(f"Debuffed visible cards -> {len(result.probes)}")
    for probe in result.probes:
        print(
            f"  [{probe.index}] {probe.label} live_id={probe.live_id} "
            f"hand={probe.hand_name}"
        )
        print(
            "      D1 actual min/expected/max -> "
            f"{probe.actual_minimum}/{probe.actual_expected:.3f}/{probe.actual_maximum}"
        )
        print(
            "      no-debuff counterfactual -> "
            f"{probe.counterfactual_minimum}/"
            f"{probe.counterfactual_expected:.3f}/"
            f"{probe.counterfactual_maximum}"
        )
        print(
            "      expected contribution suppressed -> "
            f"{probe.expected_suppressed:.3f}"
        )
        print(
            "      poker-hand structure preserved -> "
            f"{probe.structure_preserved}"
        )


def _observe_until_applicable(
    observer: LiveMemoryBalatroObserver,
    *,
    watch: bool,
    poll_seconds: float,
) -> BossDebuffValidation:
    translator = DefaultBalatroStateTranslator()
    evaluator = LiveHandDecisionEvaluator()

    while True:
        snapshot = observer.observe()
        result = analyze_boss_debuff_snapshot(
            snapshot,
            translator=translator,
            evaluator=evaluator,
        )
        if result.applicable or not watch:
            return result
        time.sleep(poll_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only live validation of boss-debuff card suppression in the "
            "production D1 score projection."
        )
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help=(
            "keep observing until a SELECTING_HAND Boss Blind checkpoint contains "
            "at least one live debuffed card"
        ),
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=DEFAULT_POLL_SECONDS,
    )
    args = parser.parse_args()

    if args.poll_seconds <= 0:
        parser.error("--poll-seconds must be positive")

    try:
        with LiveMemoryBalatroObserver() as observer:
            result = _observe_until_applicable(
                observer,
                watch=bool(args.watch),
                poll_seconds=float(args.poll_seconds),
            )
    except KeyboardInterrupt:
        print("Validation -> CANCELLED")
        return 130

    _print_validation(result)
    if not result.applicable:
        return 2
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
