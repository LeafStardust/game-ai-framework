from __future__ import annotations

import copy
import random
from dataclasses import dataclass

from games.balatro.card import BalatroCard
from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext
from games.balatro.scoring import HandScore
from games.balatro.state import BalatroState

from .effects import (
    SCORE_CHIPS,
    SCORE_MULT,
    SCORE_XMULT,
    consumable_category_feature,
)
from .joker_semantics import (
    DISCARDS_RESOURCE,
    SemanticEffectDescriptor,
    SemanticJokerBehaviorAnalyzer,
)


STATEFUL_ACTIVATION = "stateful:activation"
STATEFUL_SCALING = "stateful:scaling"
STATEFUL_DECAY = "stateful:decay"


def lifecycle_event_feature(name: str) -> str:
    return f"event:{str(name).upper()}"


@dataclass(frozen=True)
class _LifecycleCheckpoint:
    magnitudes: tuple[tuple[str, float], ...] = ()
    penalties: tuple[tuple[str, float], ...] = ()
    evidence: tuple[str, ...] = ()

    def magnitude(self, feature: str) -> float:
        return dict(self.magnitudes).get(feature, 0.0)

    def penalty(self, feature: str) -> float:
        return dict(self.penalties).get(feature, 0.0)

    @property
    def features(self) -> frozenset[str]:
        return frozenset(feature for feature, amount in self.magnitudes if amount > 0.0)


class LifecycleJokerBehaviorAnalyzer(SemanticJokerBehaviorAnalyzer):
    """Add persistent/lifecycle semantics to ordinary behavior probing.

    The semantic analyzer observes one callback at a time. Some Jokers only become
    valuable after a callback mutates their own internal state and a later callback
    consumes that state. This analyzer runs short deterministic sequences on a
    copied Joker, then compares read-only synthetic checkpoints after one and three
    repetitions. No live state, hidden draw order, or live RNG is inspected.
    """

    TRIGGER_STIMULI = (
        "PLANET_USED",
        "SHOP_REROLLED",
        "BLIND_SKIPPED",
        "ROUND_STARTED",
        "ROUND_ENDED",
    )
    EVENT_STIMULI = (
        BalatroEventType.HAND_SCORED,
        BalatroEventType.CARDS_DISCARDED,
        BalatroEventType.CARD_SOLD,
        BalatroEventType.TAROT_USED,
        BalatroEventType.BOSS_BLIND_DEFEATED,
    )
    SCORE_HANDS = (
        PokerHand.HIGH_CARD,
        PokerHand.PAIR,
        PokerHand.STRAIGHT,
        PokerHand.FLUSH,
    )

    def describe(self, joker: object) -> SemanticEffectDescriptor:
        base = super().describe(joker)
        if not isinstance(joker, Joker):
            return base

        produced = set(base.produces)
        requires = set(base.requires)
        scales_with = set(base.scales_with)
        amplifies = set(base.amplifies)
        transforms = set(base.transforms)
        penalizes = set(base.penalizes)
        evidence = set(base.evidence)
        feature_magnitudes = dict(base.feature_magnitudes)
        penalty_magnitudes = dict(base.penalty_magnitudes)

        for stimulus in self.TRIGGER_STIMULI:
            checkpoints = self._trigger_sequence(joker, stimulus)
            self._merge_sequence(
                stimulus,
                checkpoints,
                produced=produced,
                scales_with=scales_with,
                penalizes=penalizes,
                evidence=evidence,
                feature_magnitudes=feature_magnitudes,
                penalty_magnitudes=penalty_magnitudes,
            )

        for event_type in self.EVENT_STIMULI:
            stimulus = event_type.value
            checkpoints = self._event_sequence(joker, event_type)
            self._merge_sequence(
                stimulus,
                checkpoints,
                produced=produced,
                scales_with=scales_with,
                penalizes=penalizes,
                evidence=evidence,
                feature_magnitudes=feature_magnitudes,
                penalty_magnitudes=penalty_magnitudes,
            )

        for poker_hand in self.SCORE_HANDS:
            checkpoints = self._score_sequence(joker, poker_hand)
            self._merge_sequence(
                f"SCORE:{poker_hand.value}",
                checkpoints,
                produced=produced,
                scales_with=scales_with,
                penalizes=penalizes,
                evidence=evidence,
                feature_magnitudes=feature_magnitudes,
                penalty_magnitudes=penalty_magnitudes,
            )

        return SemanticEffectDescriptor(
            source=base.source,
            kind=base.kind,
            produces=frozenset(produced),
            requires=frozenset(requires),
            amplifies=frozenset(amplifies),
            scales_with=frozenset(scales_with),
            transforms=frozenset(transforms),
            evidence=tuple(sorted(evidence)),
            penalizes=frozenset(penalizes),
            feature_magnitudes=tuple(sorted(feature_magnitudes.items())),
            penalty_magnitudes=tuple(sorted(penalty_magnitudes.items())),
        )

    def _trigger_sequence(
        self,
        joker: Joker,
        trigger: str,
    ) -> tuple[_LifecycleCheckpoint, _LifecycleCheckpoint, _LifecycleCheckpoint]:
        working = copy.deepcopy(joker)
        state = self._lifecycle_state()
        baseline = self._checkpoint(working, state)
        random_state = random.getstate()
        try:
            random.seed(0)
            first = baseline
            third = baseline
            for iteration in range(1, 4):
                self._apply_stimulus(
                    working,
                    state,
                    trigger=trigger,
                )
                if iteration == 1:
                    first = self._checkpoint(working, state)
                if iteration == 3:
                    third = self._checkpoint(working, state)
        finally:
            random.setstate(random_state)
        return baseline, first, third

    def _event_sequence(
        self,
        joker: Joker,
        event_type: BalatroEventType,
    ) -> tuple[_LifecycleCheckpoint, _LifecycleCheckpoint, _LifecycleCheckpoint]:
        working = copy.deepcopy(joker)
        state = self._lifecycle_state()
        baseline = self._checkpoint(working, state)
        cards = self._neutral_cards()
        random_state = random.getstate()
        try:
            random.seed(0)
            first = baseline
            third = baseline
            for iteration in range(1, 4):
                self._apply_stimulus(
                    working,
                    state,
                    event=BalatroEvent(event_type, cards=copy.deepcopy(cards)),
                )
                if iteration == 1:
                    first = self._checkpoint(working, state)
                if iteration == 3:
                    third = self._checkpoint(working, state)
        finally:
            random.setstate(random_state)
        return baseline, first, third

    def _score_sequence(
        self,
        joker: Joker,
        poker_hand: PokerHand,
    ) -> tuple[_LifecycleCheckpoint, _LifecycleCheckpoint, _LifecycleCheckpoint]:
        working = copy.deepcopy(joker)
        state = self._lifecycle_state()
        cards = self._cards_for_hand(poker_hand)
        baseline = self._checkpoint(working, state, poker_hand=poker_hand, cards=cards)
        random_state = random.getstate()
        try:
            random.seed(0)
            first = baseline
            third = baseline
            for iteration in range(1, 4):
                self._apply_scoring_step(working, state, poker_hand, cards)
                if iteration == 1:
                    first = self._checkpoint(
                        working,
                        state,
                        poker_hand=poker_hand,
                        cards=cards,
                    )
                if iteration == 3:
                    third = self._checkpoint(
                        working,
                        state,
                        poker_hand=poker_hand,
                        cards=cards,
                    )
        finally:
            random.setstate(random_state)
        return baseline, first, third

    def _merge_sequence(
        self,
        stimulus: str,
        checkpoints: tuple[_LifecycleCheckpoint, _LifecycleCheckpoint, _LifecycleCheckpoint],
        *,
        produced: set[str],
        scales_with: set[str],
        penalizes: set[str],
        evidence: set[str],
        feature_magnitudes: dict[str, float],
        penalty_magnitudes: dict[str, float],
    ) -> None:
        baseline, first, third = checkpoints
        all_features = baseline.features | first.features | third.features
        activated = False
        scaled = False
        decayed = False

        for feature in all_features:
            before = baseline.magnitude(feature)
            after_one = first.magnitude(feature)
            after_three = third.magnitude(feature)
            maximum = max(before, after_one, after_three)
            if maximum > 0.0:
                produced.add(feature)
                feature_magnitudes[feature] = max(
                    feature_magnitudes.get(feature, 0.0),
                    maximum,
                )
            if after_one > before + 1e-12:
                activated = True
            if after_three > after_one + 1e-12:
                scaled = True
            if after_three + 1e-12 < after_one:
                decayed = True

        penalty_features = frozenset(
            feature
            for checkpoint in checkpoints
            for feature, amount in checkpoint.penalties
            if amount > 0.0
        )
        for feature in penalty_features:
            maximum = max(checkpoint.penalty(feature) for checkpoint in checkpoints)
            if maximum > 0.0:
                penalizes.add(feature)
                penalty_magnitudes[feature] = max(
                    penalty_magnitudes.get(feature, 0.0),
                    maximum,
                )

        if activated:
            produced.add(STATEFUL_ACTIVATION)
            feature_magnitudes[STATEFUL_ACTIVATION] = max(
                feature_magnitudes.get(STATEFUL_ACTIVATION, 0.0),
                1.0,
            )
            evidence.add(f"lifecycle:{stimulus}:activation")

        if scaled:
            produced.add(STATEFUL_SCALING)
            feature_magnitudes[STATEFUL_SCALING] = max(
                feature_magnitudes.get(STATEFUL_SCALING, 0.0),
                1.0,
            )
            mapped = self._stimulus_build_feature(stimulus)
            if mapped is not None:
                scales_with.add(mapped)
            evidence.add(f"lifecycle:{stimulus}:scaling")

        if decayed:
            penalizes.add(STATEFUL_DECAY)
            penalty_magnitudes[STATEFUL_DECAY] = max(
                penalty_magnitudes.get(STATEFUL_DECAY, 0.0),
                1.0,
            )
            evidence.add(f"lifecycle:{stimulus}:decay")

        for checkpoint in checkpoints:
            evidence.update(checkpoint.evidence)

    def _checkpoint(
        self,
        joker: Joker,
        state: BalatroState,
        *,
        poker_hand: PokerHand = PokerHand.HIGH_CARD,
        cards: list[BalatroCard] | None = None,
    ) -> _LifecycleCheckpoint:
        probe = copy.deepcopy(joker)
        probe_cards = copy.deepcopy(cards or self._neutral_cards())
        score = HandScore(100, 10, 1.0)
        initial_data = self._context_data(state)
        before_data = copy.deepcopy(initial_data)
        context = JokerContext(
            state=copy.deepcopy(state),
            score=score,
            poker_hand=poker_hand,
            cards=copy.deepcopy(probe_cards),
            held_cards=copy.deepcopy(probe_cards),
            trigger="HAND_SCORED",
            data=initial_data,
        )
        try:
            result = probe.apply(context)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return _LifecycleCheckpoint()

        magnitudes: dict[str, float] = {}
        penalties: dict[str, float] = {}
        evidence: set[str] = set()
        score_after = getattr(result, "score", None)
        if score_after is not None:
            if score_after.chips > 100:
                magnitudes[SCORE_CHIPS] = float(score_after.chips) - 100.0
            if score_after.mult > 10:
                magnitudes[SCORE_MULT] = float(score_after.mult) - 10.0
            if float(score_after.x_mult) > 1.0 + 1e-12:
                magnitudes[SCORE_XMULT] = float(score_after.x_mult) - 1.0

        self._interpret_data(
            before_data,
            getattr(result, "data", {}) or {},
            magnitudes=magnitudes,
            penalties=penalties,
            evidence=evidence,
            amplifies=set(),
        )
        return _LifecycleCheckpoint(
            magnitudes=tuple(sorted(magnitudes.items())),
            penalties=tuple(sorted(penalties.items())),
            evidence=tuple(sorted(evidence)),
        )

    def _apply_stimulus(
        self,
        joker: Joker,
        state: BalatroState,
        *,
        trigger: str = "",
        event: BalatroEvent | None = None,
    ) -> None:
        cards = self._neutral_cards()
        context = JokerContext(
            state=state,
            score=None,
            poker_hand=PokerHand.HIGH_CARD,
            cards=copy.deepcopy(cards),
            held_cards=copy.deepcopy(cards),
            trigger=trigger,
            event=copy.deepcopy(event),
            data=self._context_data(state),
        )
        try:
            joker.apply(context)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return

    def _apply_scoring_step(
        self,
        joker: Joker,
        state: BalatroState,
        poker_hand: PokerHand,
        cards: list[BalatroCard],
    ) -> None:
        context = JokerContext(
            state=state,
            score=HandScore(100, 10, 1.0),
            poker_hand=poker_hand,
            cards=copy.deepcopy(cards),
            held_cards=copy.deepcopy(cards),
            trigger="HAND_SCORED",
            event=BalatroEvent(BalatroEventType.HAND_SCORED, cards=copy.deepcopy(cards)),
            data=self._context_data(state),
        )
        try:
            joker.apply(context)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return

    @staticmethod
    def _lifecycle_state() -> BalatroState:
        state = BalatroState()
        state.money = 10
        return state

    @staticmethod
    def _context_data(state: BalatroState) -> dict:
        return {
            "money": int(state.money),
            "hands_remaining": int(state.hands_remaining),
            "discards_remaining": int(state.discards_remaining),
            "deck": copy.deepcopy(state.deck),
            "deck_target_size": len(state.deck),
            "probability": 1.0,
        }

    @classmethod
    def _cards_for_hand(cls, poker_hand: PokerHand) -> list[BalatroCard]:
        if poker_hand == PokerHand.PAIR:
            return [
                BalatroCard("8", "Hearts"),
                BalatroCard("8", "Spades"),
                BalatroCard("K", "Clubs"),
                BalatroCard("7", "Diamonds"),
                BalatroCard("2", "Hearts"),
            ]
        if poker_hand == PokerHand.STRAIGHT:
            return [
                BalatroCard("10", "Hearts"),
                BalatroCard("J", "Spades"),
                BalatroCard("Q", "Clubs"),
                BalatroCard("K", "Diamonds"),
                BalatroCard("A", "Hearts"),
            ]
        if poker_hand == PokerHand.FLUSH:
            return [
                BalatroCard("A", "Hearts"),
                BalatroCard("10", "Hearts"),
                BalatroCard("8", "Hearts"),
                BalatroCard("5", "Hearts"),
                BalatroCard("2", "Hearts"),
            ]
        return cls._neutral_cards()

    @staticmethod
    def _stimulus_build_feature(stimulus: str) -> str | None:
        if stimulus == "PLANET_USED":
            return consumable_category_feature("PLANET")
        if stimulus == BalatroEventType.TAROT_USED.value:
            return consumable_category_feature("TAROT")
        if stimulus == BalatroEventType.CARDS_DISCARDED.value:
            return DISCARDS_RESOURCE
        return None
