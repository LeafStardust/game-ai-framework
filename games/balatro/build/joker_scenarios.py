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
    DECK_TRANSFORM,
    SCORE_CHIPS,
    SCORE_MULT,
    SCORE_XMULT,
    enhancement_feature,
)
from .joker_lifecycle import (
    STATEFUL_ACTIVATION,
    STATEFUL_SCALING,
    LifecycleJokerBehaviorAnalyzer,
    lifecycle_event_feature,
)
from .joker_semantics import (
    SELL_VALUE_GROWTH,
    SHOP_DISCOUNT,
    SemanticEffectDescriptor,
)


PLAYED_RETRIGGER = "played:retrigger"
CARD_RULE = "card:rule"
HAND_RULE = "hand:rule"
BOSS_CONTROL = "boss:control"
SELF_DESTRUCT = "joker:self_destruct"
SURVIVAL = "run:survival"
PERMANENT_CARD_GROWTH = "deck:permanent_growth"
PROBABILITY_MULTIPLIER = "probability:multiplier"
DUPLICATE_PERMISSION = "shop:allow_duplicates"
JOKER_COPY = "joker:copy"
JOKER_DESTROY = "joker:destroy"
TAG_GENERATE = "tag:generate"


def scenario_feature(name: str) -> str:
    return f"scenario:{name}"


class _ScenarioNeighbor(Joker):
    def __init__(self, *, sell_value: int = 5, rarity: str = "UNCOMMON") -> None:
        self.sell_value = sell_value
        self.rarity = rarity

    def apply(self, context: JokerContext) -> JokerContext:
        return context


@dataclass(frozen=True)
class _Scenario:
    name: str
    trigger: str = "HAND_SCORED"
    event_type: BalatroEventType | None = None
    poker_hand: PokerHand = PokerHand.HIGH_CARD
    cards: tuple[BalatroCard, ...] = ()
    data: tuple[tuple[str, object], ...] = ()
    state_mode: str = "BASE"
    joker_neighborhood: bool = False
    post_score: bool = False
    repetitions: int = 1


@dataclass(frozen=True)
class _ScenarioResult:
    features: tuple[tuple[str, float], ...] = ()
    penalties: tuple[tuple[str, float], ...] = ()
    evidence: tuple[str, ...] = ()
    amplified: frozenset[str] = frozenset()


class ScenarioJokerBehaviorAnalyzer(LifecycleJokerBehaviorAnalyzer):
    """Probe generic public-state situations missed by one-factor analysis.

    The scenario matrix describes recurring Balatro contexts rather than Joker
    identities. It supplies public card shapes, resource boundaries, deck
    composition, owned-Joker neighborhoods and event flags that real Joker
    implementations commonly inspect. A scenario is credited only when the actual
    implementation produces an observable effect under that condition.
    """

    _SIGNAL_FEATURES = {
        "shop_free": SHOP_DISCOUNT,
        "retrigger_low_cards": PLAYED_RETRIGGER,
        "retrigger_first_card": PLAYED_RETRIGGER,
        "retrigger_played_cards": PLAYED_RETRIGGER,
        "wild_card": CARD_RULE,
        "all_cards_are_face": CARD_RULE,
        "smeared_suits": CARD_RULE,
        "all_cards_score": CARD_RULE,
        "shortcut": HAND_RULE,
        "straight_size": HAND_RULE,
        "flush_size": HAND_RULE,
        "straight_flush_size": HAND_RULE,
        "boss_blind_disabled": BOSS_CONTROL,
        "allow_duplicates": DUPLICATE_PERMISSION,
        "prevented_loss": SURVIVAL,
        "double_tag": TAG_GENERATE,
        "copy_joker": JOKER_COPY,
    }
    _SIGNAL_PENALTIES = {
        "destroy_self": SELF_DESTRUCT,
        "destroy_joker": JOKER_DESTROY,
    }
    _EVIDENCE_ONLY_SIGNALS = {
        "raised_fist_card",
        "to_do_list_hand",
    }

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

        self._promote_signals(
            produced,
            penalizes,
            evidence,
            feature_magnitudes,
            penalty_magnitudes,
        )

        for scenario in self._scenarios():
            result = self._run_scenario(joker, scenario)
            known_before = self._known_features(produced)
            scenario_known = {feature for feature, amount in result.features if amount > 0.0}
            scenario_penalties = {feature for feature, amount in result.penalties if amount > 0.0}

            for feature, amount in result.features:
                if amount <= 0.0:
                    continue
                produced.add(feature)
                feature_magnitudes[feature] = max(feature_magnitudes.get(feature, 0.0), amount)
            for feature, amount in result.penalties:
                if amount <= 0.0:
                    continue
                penalizes.add(feature)
                penalty_magnitudes[feature] = max(penalty_magnitudes.get(feature, 0.0), amount)
            amplifies.update(result.amplified)
            evidence.update(result.evidence)

            # The scenario is a useful condition only if it reveals a known effect
            # that was not already observable in the ordinary baseline probes.
            newly_known = scenario_known - known_before
            if newly_known or scenario_penalties:
                feature = scenario_feature(scenario.name)
                scales_with.add(feature)
                if any(item in {SCORE_CHIPS, SCORE_MULT, SCORE_XMULT} for item in newly_known):
                    requires.add(feature)
                evidence.add(f"scenario:{scenario.name}:active")

        self._promote_signals(
            produced,
            penalizes,
            evidence,
            feature_magnitudes,
            penalty_magnitudes,
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

    @staticmethod
    def _known_features(features: set[str]) -> set[str]:
        return {feature for feature in features if not feature.startswith("signal:")}

    def _promote_signals(
        self,
        produced: set[str],
        penalizes: set[str],
        evidence: set[str],
        feature_magnitudes: dict[str, float],
        penalty_magnitudes: dict[str, float],
    ) -> None:
        for raw in tuple(produced):
            if not raw.startswith("signal:"):
                continue
            signal = raw.split(":", 1)[1]
            if signal in self._SIGNAL_FEATURES:
                feature = self._SIGNAL_FEATURES[signal]
                produced.add(feature)
                feature_magnitudes[feature] = max(feature_magnitudes.get(feature, 0.0), 1.0)
                produced.discard(raw)
                evidence.add(f"semantic:{signal}->{feature}")
            elif signal in self._SIGNAL_PENALTIES:
                feature = self._SIGNAL_PENALTIES[signal]
                penalizes.add(feature)
                penalty_magnitudes[feature] = max(penalty_magnitudes.get(feature, 0.0), 1.0)
                produced.discard(raw)
                evidence.add(f"semantic:{signal}->{feature}")
            elif signal == "raised_fist_mult":
                produced.add(SCORE_MULT)
                feature_magnitudes[SCORE_MULT] = max(feature_magnitudes.get(SCORE_MULT, 0.0), 1.0)
                produced.discard(raw)
                evidence.add("semantic:raised_fist_mult->score:mult")
            elif signal in self._EVIDENCE_ONLY_SIGNALS:
                produced.discard(raw)
                evidence.add(f"semantic:{signal}:evidence_only")

    def _run_scenario(self, joker: Joker, scenario: _Scenario) -> _ScenarioResult:
        working = copy.deepcopy(joker)
        state = self._scenario_state(scenario.state_mode)
        if scenario.joker_neighborhood:
            state.jokers = [
                working,
                _ScenarioNeighbor(sell_value=5, rarity="UNCOMMON"),
                _ScenarioNeighbor(sell_value=8, rarity="UNCOMMON"),
            ]

        cards = list(copy.deepcopy(scenario.cards or tuple(self._neutral_cards())))
        before_cards = copy.deepcopy(cards)
        data = self._context_data(state)
        data.update(copy.deepcopy(dict(scenario.data)))
        if scenario.name == "self_sale":
            data["sold_joker"] = working

        before_data = copy.deepcopy(data)
        # Identity-valued fields are probe inputs, not Joker outputs. Preserve the
        # exact reference across the before/after comparison so deepcopy itself does
        # not manufacture a false semantic signal for every Joker.
        if "sold_joker" in data:
            before_data["sold_joker"] = data["sold_joker"]
        before_owned = copy.deepcopy(data.get("owned_cards", []))
        score = HandScore(100, 10, 1.0)
        event = (
            BalatroEvent(scenario.event_type, cards=copy.deepcopy(cards))
            if scenario.event_type is not None
            else None
        )

        random_state = random.getstate()
        try:
            random.seed(0)
            result = None
            for _ in range(max(1, scenario.repetitions)):
                context = JokerContext(
                    state=state,
                    score=score,
                    poker_hand=scenario.poker_hand,
                    cards=cards,
                    held_cards=copy.deepcopy(cards),
                    trigger=scenario.trigger,
                    event=copy.deepcopy(event),
                    data=data,
                )
                result = working.apply(context)
                data = getattr(result, "data", data) or data

            if scenario.post_score:
                score = HandScore(100, 10, 1.0)
                context = JokerContext(
                    state=state,
                    score=score,
                    poker_hand=scenario.poker_hand,
                    cards=copy.deepcopy(cards),
                    held_cards=copy.deepcopy(cards),
                    trigger="HAND_SCORED",
                    data=data,
                )
                result = working.apply(context)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return _ScenarioResult()
        finally:
            random.setstate(random_state)

        if result is None:
            return _ScenarioResult()

        features: dict[str, float] = {}
        penalties: dict[str, float] = {}
        evidence: set[str] = set()
        amplified: set[str] = set()

        score_after = getattr(result, "score", None)
        if score_after is not None:
            self._signed_delta(SCORE_CHIPS, float(score_after.chips) - 100.0, features, penalties)
            self._signed_delta(SCORE_MULT, float(score_after.mult) - 10.0, features, penalties)
            self._signed_delta(SCORE_XMULT, float(score_after.x_mult) - 1.0, features, penalties)

        self._interpret_data(
            before_data,
            getattr(result, "data", {}) or {},
            magnitudes=features,
            penalties=penalties,
            evidence=evidence,
            amplifies=amplified,
        )

        self._detect_card_mutations(before_cards, getattr(result, "cards", cards), features, evidence)
        self._detect_owned_sell_value(before_owned, (getattr(result, "data", {}) or {}).get("owned_cards", []), features, evidence)

        return _ScenarioResult(
            features=tuple(sorted(features.items())),
            penalties=tuple(sorted(penalties.items())),
            evidence=tuple(sorted(evidence)),
            amplified=frozenset(amplified),
        )

    @classmethod
    def _detect_card_mutations(
        cls,
        before: list[BalatroCard],
        after: list[BalatroCard],
        features: dict[str, float],
        evidence: set[str],
    ) -> None:
        for prior, current in zip(before, after):
            if prior.enhancement != current.enhancement and current.enhancement:
                features[DECK_TRANSFORM] = max(features.get(DECK_TRANSFORM, 0.0), 1.0)
                feature = enhancement_feature(str(current.enhancement))
                features[feature] = max(features.get(feature, 0.0), 1.0)
                evidence.add(f"scenario:enhancement:{prior.enhancement}->{current.enhancement}")
            before_bonus = float(getattr(prior, "permanent_bonus", 0) or 0)
            after_bonus = float(getattr(current, "permanent_bonus", 0) or 0)
            if after_bonus > before_bonus:
                features[PERMANENT_CARD_GROWTH] = max(
                    features.get(PERMANENT_CARD_GROWTH, 0.0),
                    after_bonus - before_bonus,
                )
                evidence.add(f"scenario:permanent_bonus:+{after_bonus - before_bonus:g}")

    @staticmethod
    def _detect_owned_sell_value(
        before: list[object],
        after: list[object],
        features: dict[str, float],
        evidence: set[str],
    ) -> None:
        total_before = sum(float(getattr(card, "sell_value", 0) or 0) for card in before)
        total_after = sum(float(getattr(card, "sell_value", 0) or 0) for card in after)
        if total_after > total_before:
            delta = total_after - total_before
            features[SELL_VALUE_GROWTH] = max(features.get(SELL_VALUE_GROWTH, 0.0), delta)
            evidence.add(f"scenario:owned_sell_value:+{delta:g}")

    @staticmethod
    def _signed_delta(
        feature: str,
        delta: float,
        features: dict[str, float],
        penalties: dict[str, float],
    ) -> None:
        if delta > 1e-12:
            features[feature] = max(features.get(feature, 0.0), delta)
        elif delta < -1e-12:
            penalties[feature] = max(penalties.get(feature, 0.0), abs(delta))

    @classmethod
    def _scenario_state(cls, mode: str) -> BalatroState:
        state = BalatroState()
        state.money = 20
        if mode == "ENHANCED_DECK":
            for card in state.deck[:20]:
                card.enhancement = "Mult"
        elif mode == "STEEL_DECK":
            for card in state.deck[:12]:
                card.enhancement = "Steel"
        elif mode == "SHORT_DECK":
            state.deck = state.deck[:40]
        elif mode == "GLASS_DESTROYED":
            state.glass_cards_destroyed = 4
        return state

    @classmethod
    def _scenarios(cls) -> tuple[_Scenario, ...]:
        two_pair = (
            BalatroCard("8", "Hearts"),
            BalatroCard("8", "Spades"),
            BalatroCard("K", "Clubs"),
            BalatroCard("K", "Diamonds"),
            BalatroCard("2", "Hearts"),
        )
        face_cards = (
            BalatroCard("J", "Hearts"),
            BalatroCard("Q", "Spades"),
            BalatroCard("K", "Clubs"),
        )
        low_cards = tuple(BalatroCard(rank, "Hearts") for rank in ("2", "3", "4", "5", "6"))
        gold_cards = tuple(
            BalatroCard(rank, "Hearts", enhancement="Gold")
            for rank in ("J", "Q", "K", "9", "2")
        )
        return (
            _Scenario("joker_neighborhood", joker_neighborhood=True),
            _Scenario("hands_exhausted", data=(("hands_remaining", 0),)),
            _Scenario("discards_exhausted", data=(("discards_remaining", 0),)),
            _Scenario("repeated_hand", data=(("poker_hand_played_twice", True),)),
            _Scenario("two_pair", poker_hand=PokerHand.TWO_PAIR, cards=two_pair),
            _Scenario("three_cards", cards=tuple(cls._neutral_cards()[:3])),
            _Scenario("four_cards", cards=tuple(cls._neutral_cards()[:4])),
            _Scenario("single_six", cards=(BalatroCard("6", "Hearts"),)),
            _Scenario(
                "single_six_discard",
                trigger="DISCARD",
                cards=(BalatroCard("6", "Hearts"),),
                data=(("discard_number", 1), ("trading_card_triggered", False), ("sixth_sense_triggered", False)),
                post_score=True,
            ),
            _Scenario("faces_discarded", trigger="DISCARD", cards=face_cards, post_score=True),
            _Scenario("low_cards", cards=low_cards),
            _Scenario("gold_cards", cards=gold_cards),
            _Scenario("enhanced_deck", state_mode="ENHANCED_DECK"),
            _Scenario("steel_deck", state_mode="STEEL_DECK"),
            _Scenario("short_deck", state_mode="SHORT_DECK", data=(("deck_target_size", 52),)),
            _Scenario("glass_destroyed", state_mode="GLASS_DESTROYED"),
            _Scenario("used_planets", trigger="ROUND_ENDED", data=(("used_planets", ("Mercury", "Venus", "Earth")),), post_score=True),
            _Scenario("mail_rebate", trigger="DISCARD", cards=(BalatroCard("7", "Hearts"), BalatroCard("7", "Clubs")), data=(("mail_in_rebate_rank", "7"),), post_score=True),
            _Scenario("destroyed_faces", event_type=BalatroEventType.CARDS_ADDED, data=(("destroyed_cards", face_cards),), post_score=True),
            _Scenario("run_failed", trigger="RUN_FAILED", data=(("score", 25), ("required_score", 100))),
            _Scenario("self_sale", trigger="SOLD"),
            _Scenario("boss_selected", trigger="BOSS_BLIND_SELECTED"),
            _Scenario("probability_check", trigger="PROBABILITY_CHECK", data=(("probability", 0.25),)),
            _Scenario("first_discard", trigger="DISCARD", data=(("discard_number", 1),), post_score=True),
            _Scenario("hand_played_cycle", trigger="HAND_PLAYED", repetitions=6),
            _Scenario("long_discard_cycle", event_type=BalatroEventType.CARDS_DISCARDED, repetitions=5, post_score=True),
        )
