from __future__ import annotations

import copy
from dataclasses import dataclass

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.joker import Joker
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState

from .literal_score_expectation import literal_expected_score
from .semantic_synergy import SemanticContextualJokerSynergyEvaluator
from .synergy import ContextualBuildEvaluation, ContextualJokerSynergyEvaluator


@dataclass(frozen=True)
class JokerBuildValueWeights:
    """Combine immediate scoring with contextual mechanical semantics."""

    direct_scoring_gain: float = 6.0
    contextual_gain: float = 1.0
    direct_scoring_cap: float = 12.0


@dataclass(frozen=True)
class JokerBuildValue:
    joker: str
    direct_scoring_gain: float
    direct_scoring_value: float
    contextual: ContextualBuildEvaluation
    total_gain: float
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class JokerReplacementOption:
    replace_index: int
    replace_joker: str
    incumbent_value: JokerBuildValue
    candidate_value: JokerBuildValue
    build_delta: float
    rationale: tuple[str, ...]
    eligible: bool = True
    blocked_reason: str | None = None


@dataclass(frozen=True)
class JokerBuildTransition:
    """Build-only recommendation for adding/replacing one Joker.

    ``ADD`` means the candidate can be added without displacing an incumbent and
    contributes positive build value. That includes an ordinary free Joker slot and
    Balatro's slot-neutral Negative edition. ``REPLACE`` identifies the best occupied
    slot under a common baseline. ``HOLD`` means no positive build transition was
    found. None of these values authorize a live sell/buy; D2/B5 must still apply
    economics and execution guards before acting.
    """

    action: str
    candidate: str
    candidate_value: JokerBuildValue
    replacement: JokerReplacementOption | None = None
    alternatives: tuple[JokerReplacementOption, ...] = ()
    rationale: tuple[str, ...] = ()


class JokerBuildValueEvaluator:
    """Measure one Joker against the current complete build.

    Representative probes compare the whole literal scoring stack before and after
    adding the candidate. Played-card chips are included, and public stochastic
    scoring mechanics use analytic outcome expectation rather than sampled RNG or
    deterministic failure. When public hand-play history exists, probes are weighted
    toward the hands the run actually plays. B3 remains a separate structural/long-
    horizon contribution and never becomes chips/Mult/XMult.
    """

    PROBES = (
        (PokerHand.HIGH_CARD, (BalatroCard("A", "Spades"), BalatroCard("K", "Hearts"), BalatroCard("9", "Clubs"), BalatroCard("5", "Diamonds"), BalatroCard("2", "Spades"))),
        (PokerHand.PAIR, (BalatroCard("8", "Hearts"), BalatroCard("8", "Spades"), BalatroCard("K", "Clubs"), BalatroCard("7", "Diamonds"), BalatroCard("2", "Hearts"))),
        (PokerHand.TWO_PAIR, (BalatroCard("A", "Hearts"), BalatroCard("A", "Spades"), BalatroCard("K", "Clubs"), BalatroCard("K", "Diamonds"), BalatroCard("2", "Hearts"))),
        (PokerHand.THREE_OF_A_KIND, (BalatroCard("Q", "Hearts"), BalatroCard("Q", "Spades"), BalatroCard("Q", "Clubs"), BalatroCard("7", "Diamonds"), BalatroCard("2", "Hearts"))),
        (PokerHand.STRAIGHT, (BalatroCard("10", "Hearts"), BalatroCard("J", "Spades"), BalatroCard("Q", "Clubs"), BalatroCard("K", "Diamonds"), BalatroCard("A", "Hearts"))),
        (PokerHand.FLUSH, (BalatroCard("A", "Hearts"), BalatroCard("10", "Hearts"), BalatroCard("8", "Hearts"), BalatroCard("5", "Hearts"), BalatroCard("2", "Hearts"))),
        (PokerHand.FULL_HOUSE, (BalatroCard("K", "Hearts"), BalatroCard("K", "Spades"), BalatroCard("K", "Clubs"), BalatroCard("8", "Diamonds"), BalatroCard("8", "Hearts"))),
        (PokerHand.FOUR_OF_A_KIND, (BalatroCard("8", "Hearts"), BalatroCard("8", "Spades"), BalatroCard("8", "Clubs"), BalatroCard("8", "Diamonds"), BalatroCard("A", "Hearts"))),
    )
    _OBSERVED_HAND_PRIOR_WEIGHT = 0.25

    def __init__(self, *, scorer: BalatroScorer | None = None, contextual: ContextualJokerSynergyEvaluator | None = None, weights: JokerBuildValueWeights | None = None) -> None:
        self.scorer = scorer or BalatroScorer()
        self.contextual = contextual or SemanticContextualJokerSynergyEvaluator()
        self.weights = weights or JokerBuildValueWeights()

    def evaluate(self, state: BalatroState, joker: object) -> JokerBuildValue:
        if not isinstance(joker, Joker):
            contextual = self.contextual.evaluate(joker, state)
            return JokerBuildValue(joker=type(joker).__name__, direct_scoring_gain=0.0, direct_scoring_value=0.0, contextual=contextual, total_gain=0.0, rationale=("candidate is not a modeled Joker",))

        direct_gain = self._direct_scoring_gain(state, joker)
        direct_value = max(-self.weights.direct_scoring_cap, min(self.weights.direct_scoring_cap, direct_gain * self.weights.direct_scoring_gain))
        contextual = self.contextual.evaluate(joker, state)
        contextual_value = contextual.total_gain * self.weights.contextual_gain
        total = direct_value + contextual_value
        rationale = [f"representative whole-build scoring gain={direct_gain:.6f} value={direct_value:.3f}", f"B3 intrinsic={contextual.intrinsic_gain:.3f}", f"B3 interaction={contextual.interaction_gain:.3f}"]
        rationale.extend(contextual.rationale)
        return JokerBuildValue(joker=type(joker).__name__, direct_scoring_gain=direct_gain, direct_scoring_value=direct_value, contextual=contextual, total_gain=total, rationale=tuple(rationale))

    @staticmethod
    def _hand_key(value: object) -> str:
        return "_".join(str(value or "").strip().upper().replace("-", " ").replace("_", " ").split())

    def _probe_weights(self, state: BalatroState) -> dict[str, float] | None:
        raw = getattr(state, "hand_play_counts", {}) or {}
        counts: dict[str, float] = {}
        try:
            items = raw.items()
        except AttributeError:
            try:
                items = iter(raw)
            except TypeError:
                return None
        for key, value in items:
            try:
                count = max(0.0, float(value or 0.0))
            except (TypeError, ValueError):
                continue
            if count > 0.0:
                counts[self._hand_key(key)] = counts.get(self._hand_key(key), 0.0) + count
        return counts or None

    def _direct_scoring_gain(self, state: BalatroState, joker: Joker) -> float:
        weighted_gain = 0.0
        total_weight = 0.0
        observed = self._probe_weights(state)

        for hand, template_cards in self._scoring_probes(state):
            cards = copy.deepcopy(list(template_cards))
            before_state = copy.deepcopy(state)
            before_state.hand = copy.deepcopy(cards)
            after_state = copy.deepcopy(before_state)
            after_state.jokers.append(copy.deepcopy(joker))

            try:
                before = literal_expected_score(
                    before_state,
                    hand,
                    cards,
                    scorer=self.scorer,
                )
                after = literal_expected_score(
                    after_state,
                    hand,
                    cards,
                    scorer=self.scorer,
                )
            except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
                continue

            gain = (float(after) - float(before)) / max(abs(float(before)), 1.0)
            if observed is None:
                weight = 1.0
            else:
                weight = self._OBSERVED_HAND_PRIOR_WEIGHT + observed.get(self._hand_key(hand.value), 0.0)
            weighted_gain += gain * weight
            total_weight += weight

        return weighted_gain / total_weight if total_weight > 0.0 else 0.0

    def _scoring_probes(self, state: BalatroState):
        """Return representative hands used to value a candidate Joker."""
        return self.PROBES


class JokerBuildTransitionPlanner:
    """Compare every legal slot transition against the same remaining build.

    Replacement is intentionally evaluated by removing one incumbent first and
    then comparing re-adding that incumbent against adding the candidate. This
    avoids the common error of ranking Jokers in isolation and selling a critical
    synergy component because another Joker has a higher standalone score.

    Canonical projected Bond composition evaluates preservation and pivot cost after
    this mechanically local transition comparison.
    """

    def __init__(self, *, evaluator: JokerBuildValueEvaluator | None = None, minimum_add_gain: float = 0.0, minimum_replacement_delta: float = 0.0) -> None:
        self.evaluator = evaluator or JokerBuildValueEvaluator()
        self.minimum_add_gain = float(minimum_add_gain)
        self.minimum_replacement_delta = float(minimum_replacement_delta)

    def plan(self, state: BalatroState, candidate: object) -> JokerBuildTransition:
        candidate_name = type(candidate).__name__
        candidate_value = self.evaluator.evaluate(state, candidate)

        if not isinstance(candidate, Joker):
            return JokerBuildTransition(action="HOLD", candidate=candidate_name, candidate_value=candidate_value, rationale=("candidate is not a modeled Joker",))

        free_slots = max(0, int(state.joker_slots) - len(state.jokers))
        slot_neutral = joker_has_negative_edition(candidate)
        if free_slots > 0 or slot_neutral:
            if candidate_value.total_gain > self.minimum_add_gain:
                slot_note = "Negative edition is slot-neutral" if slot_neutral and free_slots <= 0 else "free Joker slot available"
                return JokerBuildTransition(action="ADD", candidate=candidate_name, candidate_value=candidate_value, rationale=(f"{slot_note}; build gain={candidate_value.total_gain:.3f}",))
            return JokerBuildTransition(action="HOLD", candidate=candidate_name, candidate_value=candidate_value, rationale=(f"candidate build gain {candidate_value.total_gain:.3f} does not exceed add threshold {self.minimum_add_gain:.3f}",))

        options: list[JokerReplacementOption] = []
        for index, incumbent in enumerate(state.jokers):
            if not isinstance(incumbent, Joker):
                continue

            baseline = copy.deepcopy(state)
            removed = baseline.jokers.pop(index)
            incumbent_value = self.evaluator.evaluate(baseline, removed)
            replacement_value = self.evaluator.evaluate(baseline, candidate)
            delta = replacement_value.total_gain - incumbent_value.total_gain
            negative_retention = joker_has_negative_edition(incumbent)
            blocked_reason = "Negative Joker is retention-protected and cannot create a replacement slot; selling it also removes its extra slot" if negative_retention else None
            rationale = [f"common baseline excludes slot {index} {type(incumbent).__name__}", f"candidate gain={replacement_value.total_gain:.3f}", f"incumbent gain={incumbent_value.total_gain:.3f}", f"replacement delta={delta:.3f}"]
            if blocked_reason is not None:
                rationale.extend((blocked_reason, "Negative retention result=PROTECTED_FROM_REPLACEMENT"))
            options.append(JokerReplacementOption(replace_index=index, replace_joker=type(incumbent).__name__, incumbent_value=incumbent_value, candidate_value=replacement_value, build_delta=delta, rationale=tuple(rationale), eligible=not negative_retention, blocked_reason=blocked_reason))

        ranked = tuple(sorted(options, key=lambda option: (-option.build_delta, option.replace_index)))
        eligible_ranked = tuple(option for option in ranked if option.eligible)
        best = eligible_ranked[0] if eligible_ranked else None
        if best is not None and best.build_delta > self.minimum_replacement_delta:
            protected = sum(not option.eligible for option in ranked)
            return JokerBuildTransition(action="REPLACE", candidate=candidate_name, candidate_value=candidate_value, replacement=best, alternatives=ranked, rationale=(f"best whole-build replacement delta={best.build_delta:.3f}", f"replace slot {best.replace_index} {best.replace_joker}", f"Negative retention protected replacement options={protected}"))

        best_delta = best.build_delta if best is not None else float("-inf")
        protected = sum(not option.eligible for option in ranked)
        return JokerBuildTransition(action="HOLD", candidate=candidate_name, candidate_value=candidate_value, alternatives=ranked, rationale=(f"best replacement delta={best_delta:.3f}; threshold={self.minimum_replacement_delta:.3f}", f"Negative retention protected replacement options={protected}"))
