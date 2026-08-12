from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Iterable

from games.balatro.card import BalatroCard
from games.balatro.consumable import Consumable, PlanetCard
from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext
from games.balatro.scoring import HandScore
from games.balatro.state import BalatroState

from .effects import (
    CONSUMABLE_GENERATE,
    DECK_REMOVE,
    ECONOMY,
    HAND_LEVEL,
    HELD_EFFECT,
    HELD_RETRIGGER,
    JOKER_GENERATE,
    SCORE_CHIPS,
    SCORE_MULT,
    SCORE_XMULT,
    EffectDescriptor,
    JokerBehaviorAnalyzer,
    consumable_category_feature,
)


HANDS_RESOURCE = "resource:hands"
DISCARDS_RESOURCE = "resource:discards"
HAND_SIZE_RESOURCE = "resource:hand_size"
FREE_REROLL_RESOURCE = "resource:free_reroll"
CARD_GENERATE = "deck:card_generate"
CONSUMABLE_DUPLICATE = "consumable:duplicate"
SELL_VALUE_GROWTH = "economy:sell_value"
SHOP_DISCOUNT = "economy:shop_discount"
DEBT_CAPACITY = "economy:debt_capacity"


@dataclass(frozen=True)
class SemanticEffectDescriptor(EffectDescriptor):
    """Effect descriptor with explicit negative tradeoffs and observed magnitudes."""

    penalizes: frozenset[str] = frozenset()
    feature_magnitudes: tuple[tuple[str, float], ...] = ()
    penalty_magnitudes: tuple[tuple[str, float], ...] = ()

    def feature_magnitude(self, feature: str) -> float:
        return dict(self.feature_magnitudes).get(feature, 1.0)

    def penalty_magnitude(self, feature: str) -> float:
        return dict(self.penalty_magnitudes).get(feature, 1.0)


@dataclass(frozen=True)
class _SemanticProbeResult:
    magnitudes: tuple[tuple[str, float], ...] = ()
    penalties: tuple[tuple[str, float], ...] = ()
    evidence: tuple[str, ...] = ()
    amplifies: frozenset[str] = frozenset()

    def magnitude(self, feature: str) -> float:
        return dict(self.magnitudes).get(feature, 0.0)

    @property
    def produced(self) -> frozenset[str]:
        return frozenset(feature for feature, amount in self.magnitudes if amount > 0.0)

    @property
    def penalized(self) -> frozenset[str]:
        return frozenset(feature for feature, amount in self.penalties if amount > 0.0)


class SemanticJokerBehaviorAnalyzer(JokerBehaviorAnalyzer):
    """Extend behavior probing to non-scoring and event-driven Joker effects.

    The base analyzer still owns rank/suit/hand conditional inference. This layer
    interprets observable ``JokerContext.data`` mutations, probes modeled runtime
    triggers/events, and records positive/negative resource effects separately.
    All probes run on synthetic state with deterministic seeds; they never inspect
    live RNG or future draw order.
    """

    TRIGGERS = (
        "HAND_SCORED",
        "BLIND_SELECTED",
        "BOOSTER_OPENED",
        "ROUND_STARTED",
        "ROUND_ENDED",
        "SHOP_ENTERED",
        "SHOP_REROLLED",
        "JOKER_ACQUIRED",
        "INTEREST_CALCULATED",
        "DISCARD",
        "SOLD",
        "BOSS_BLIND_SELECTED",
        "BOSS_BLIND_DEFEATED",
        "PLANET_USED",
        "BLIND_SKIPPED",
        "PROBABILITY_CHECK",
    )
    CAPABILITY_SEEDS = (0, 1)

    def describe(self, joker: object) -> SemanticEffectDescriptor:
        if not isinstance(joker, Joker):
            return SemanticEffectDescriptor(source=type(joker).__name__, kind="UNKNOWN")

        base = super().describe(joker)
        results: list[_SemanticProbeResult] = []
        cards = self._neutral_cards()

        for trigger in self.TRIGGERS:
            for seed in self.CAPABILITY_SEEDS:
                results.append(
                    self._run_semantic_probe(
                        joker,
                        cards=cards,
                        held_cards=cards,
                        poker_hand=PokerHand.HIGH_CARD,
                        trigger=trigger,
                        random_seed=seed,
                    )
                )

        for event_type in BalatroEventType:
            for seed in self.CAPABILITY_SEEDS:
                results.append(
                    self._run_semantic_probe(
                        joker,
                        cards=cards,
                        held_cards=cards,
                        poker_hand=PokerHand.HIGH_CARD,
                        trigger="",
                        event=BalatroEvent(event_type, cards=copy.deepcopy(cards)),
                        random_seed=seed,
                    )
                )

        produced = set(base.produces)
        penalizes: set[str] = set()
        evidence = set(base.evidence)
        amplifies = set(base.amplifies)
        feature_magnitudes: dict[str, float] = {}
        penalty_magnitudes: dict[str, float] = {}

        for result in results:
            produced.update(result.produced)
            penalizes.update(result.penalized)
            evidence.update(result.evidence)
            amplifies.update(result.amplifies)
            for feature, amount in result.magnitudes:
                feature_magnitudes[feature] = max(feature_magnitudes.get(feature, 0.0), amount)
            for feature, amount in result.penalties:
                penalty_magnitudes[feature] = max(penalty_magnitudes.get(feature, 0.0), amount)

        return SemanticEffectDescriptor(
            source=base.source,
            kind=base.kind,
            produces=frozenset(produced),
            requires=base.requires,
            amplifies=frozenset(amplifies),
            scales_with=base.scales_with,
            transforms=base.transforms,
            evidence=tuple(sorted(evidence)),
            penalizes=frozenset(penalizes),
            feature_magnitudes=tuple(sorted(feature_magnitudes.items())),
            penalty_magnitudes=tuple(sorted(penalty_magnitudes.items())),
        )

    def _probe(
        self,
        joker: Joker,
        *,
        cards: list[BalatroCard],
        held_cards: list[BalatroCard],
        poker_hand: PokerHand = PokerHand.HIGH_CARD,
    ) -> _SemanticProbeResult:
        # Keep the base analyzer's conditional probes on the canonical hand-score
        # trigger. Event capabilities are added separately by ``describe``.
        return self._run_semantic_probe(
            joker,
            cards=cards,
            held_cards=held_cards,
            poker_hand=poker_hand,
            trigger="HAND_SCORED",
            random_seed=0,
        )

    def _run_semantic_probe(
        self,
        joker: Joker,
        *,
        cards: list[BalatroCard],
        held_cards: list[BalatroCard],
        poker_hand: PokerHand,
        trigger: str,
        event: BalatroEvent | None = None,
        random_seed: int = 0,
    ) -> _SemanticProbeResult:
        state = BalatroState()
        state.hand = copy.deepcopy(cards)
        score = HandScore(100, 10, 1.0)

        probe_consumable = PlanetCard("Probe Planet", "PAIR", chips=10, mult=1)
        owned_card = BalatroCard("K", "Hearts")
        owned_card.sell_value = 1
        initial_data = {
            "money": int(state.money),
            "discards_remaining": int(state.discards_remaining),
            "hands_remaining": int(state.hands_remaining),
            "consumable_slots_full": False,
            "hand_full": False,
            "boss_blind": False,
            "deck": copy.deepcopy(state.deck),
            "deck_target_size": len(state.deck),
            "consumables": [probe_consumable],
            "owned_cards": [owned_card],
            "probability": 1.0,
        }
        before_data = copy.deepcopy(initial_data)
        context = JokerContext(
            state=state,
            score=score,
            poker_hand=poker_hand,
            cards=copy.deepcopy(cards),
            held_cards=copy.deepcopy(held_cards),
            trigger=trigger,
            event=copy.deepcopy(event),
            data=initial_data,
        )

        working = copy.deepcopy(joker)
        initial_sell_value = self._number(getattr(working, "sell_value", None))
        random_state = random.getstate()
        try:
            random.seed(random_seed)
            result = working.apply(context)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return _SemanticProbeResult()
        finally:
            random.setstate(random_state)

        magnitudes: dict[str, float] = {}
        penalties: dict[str, float] = {}
        evidence: set[str] = set()
        amplifies: set[str] = set()

        score_after = getattr(result, "score", None)
        if score_after is not None:
            if score_after.chips != 100:
                magnitudes[SCORE_CHIPS] = abs(float(score_after.chips) - 100.0)
            if score_after.mult != 10:
                magnitudes[SCORE_MULT] = abs(float(score_after.mult) - 10.0)
            if abs(float(score_after.x_mult) - 1.0) > 1e-12:
                magnitudes[SCORE_XMULT] = abs(float(score_after.x_mult) - 1.0)

        data = getattr(result, "data", {}) or {}
        self._interpret_data(
            before_data,
            data,
            magnitudes=magnitudes,
            penalties=penalties,
            evidence=evidence,
            amplifies=amplifies,
        )

        state_money_after = self._number(getattr(result.state, "money", state.money))
        if state_money_after is not None and state_money_after != float(state.money):
            delta = state_money_after - float(state.money)
            self._record_signed(ECONOMY, delta, magnitudes, penalties)
            evidence.add(f"state:money_delta:{delta:g}")

        final_sell_value = self._number(getattr(working, "sell_value", None))
        if initial_sell_value is not None and final_sell_value is not None:
            delta = final_sell_value - initial_sell_value
            if delta:
                self._record_signed(SELL_VALUE_GROWTH, delta, magnitudes, penalties)
                evidence.add(f"joker:sell_value_delta:{delta:g}")

        return _SemanticProbeResult(
            magnitudes=tuple(sorted(magnitudes.items())),
            penalties=tuple(sorted(penalties.items())),
            evidence=tuple(sorted(evidence)),
            amplifies=frozenset(amplifies),
        )

    def _interpret_data(
        self,
        before: dict,
        after: dict,
        *,
        magnitudes: dict[str, float],
        penalties: dict[str, float],
        evidence: set[str],
        amplifies: set[str],
    ) -> None:
        handled: set[str] = set()

        def changed(key: str) -> bool:
            return key in after and after.get(key) != before.get(key)

        if changed("retrigger_held_abilities") and after.get("retrigger_held_abilities"):
            amount = self._positive_amount(after.get("retrigger_held_abilities"))
            magnitudes[HELD_RETRIGGER] = max(magnitudes.get(HELD_RETRIGGER, 0.0), amount)
            amplifies.add(HELD_EFFECT)
            evidence.add("context:retrigger_held_abilities")
            handled.add("retrigger_held_abilities")

        generation_keys = {
            "created_tarot_cards": "TAROT",
            "created_planet_cards": "PLANET",
            "created_spectral_cards": "SPECTRAL",
        }
        for key, category in generation_keys.items():
            if not changed(key) or not after.get(key):
                continue
            amount = self._collection_amount(after.get(key))
            self._record_positive(CONSUMABLE_GENERATE, amount, magnitudes)
            self._record_positive(consumable_category_feature(category), amount, magnitudes)
            evidence.add(f"context:{key}")
            handled.add(key)

        if changed("created_consumables") and after.get("created_consumables"):
            created = after.get("created_consumables")
            amount = self._collection_amount(created)
            self._record_positive(CONSUMABLE_GENERATE, amount, magnitudes)
            for category in self._consumable_categories(created):
                self._record_positive(consumable_category_feature(category), 1.0, magnitudes)
            evidence.add("context:created_consumables")
            handled.add("created_consumables")

        if changed("create_negative_copy") and after.get("create_negative_copy") is not None:
            self._record_positive(CONSUMABLE_GENERATE, 1.0, magnitudes)
            self._record_positive(CONSUMABLE_DUPLICATE, 1.0, magnitudes)
            for category in self._consumable_categories([after.get("create_negative_copy")]):
                self._record_positive(consumable_category_feature(category), 1.0, magnitudes)
            evidence.add("context:create_negative_copy")
            handled.add("create_negative_copy")

        for key in ("create_random_jokers", "create_joker"):
            if not changed(key) or not after.get(key):
                continue
            self._record_positive(JOKER_GENERATE, self._positive_amount(after.get(key)), magnitudes)
            evidence.add(f"context:{key}")
            handled.add(key)

        for key in ("created_cards", "copied_cards"):
            if not changed(key) or not after.get(key):
                continue
            amount = self._collection_amount(after.get(key))
            self._record_positive(CARD_GENERATE, amount, magnitudes)
            evidence.add(f"context:{key}")
            handled.add(key)

        if changed("destroyed_cards") and after.get("destroyed_cards"):
            self._record_positive(DECK_REMOVE, self._collection_amount(after.get("destroyed_cards")), magnitudes)
            evidence.add("context:destroyed_cards")
            handled.add("destroyed_cards")

        if changed("level_ups") and after.get("level_ups"):
            self._record_positive(HAND_LEVEL, self._collection_amount(after.get("level_ups")), magnitudes)
            evidence.add("context:level_ups")
            handled.add("level_ups")

        # Context money is the modeled output channel used by several economy
        # Jokers. Treat named *_money accumulators the same way when they change.
        for key, value in after.items():
            if key != "money" and not key.endswith("_money"):
                continue
            if not changed(key):
                continue
            before_value = self._number(before.get(key)) or 0.0
            after_value = self._number(value)
            if after_value is None:
                continue
            delta = after_value - before_value
            self._record_signed(ECONOMY, delta, magnitudes, penalties)
            evidence.add(f"context:{key}:delta:{delta:g}")
            handled.add(key)

        signed_resources = {
            "hand_size_modifier": HAND_SIZE_RESOURCE,
            "hands_gained": HANDS_RESOURCE,
            "hands_per_round_modifier": HANDS_RESOURCE,
            "discards_per_round_modifier": DISCARDS_RESOURCE,
            "free_rerolls": FREE_REROLL_RESOURCE,
            "interest_bonus": ECONOMY,
        }
        for key, feature in signed_resources.items():
            if not changed(key):
                continue
            before_value = self._number(before.get(key)) or 0.0
            after_value = self._number(after.get(key))
            if after_value is None:
                continue
            delta = after_value - before_value
            self._record_signed(feature, delta, magnitudes, penalties)
            evidence.add(f"context:{key}:delta:{delta:g}")
            handled.add(key)

        if changed("discards_remaining"):
            before_value = self._number(before.get("discards_remaining")) or 0.0
            after_value = self._number(after.get("discards_remaining"))
            if after_value is not None:
                delta = after_value - before_value
                self._record_signed(DISCARDS_RESOURCE, delta, magnitudes, penalties)
                evidence.add(f"context:discards_remaining:delta:{delta:g}")
            handled.add("discards_remaining")

        if changed("max_debt"):
            before_value = self._number(before.get("max_debt")) or 0.0
            after_value = self._number(after.get("max_debt"))
            if after_value is not None:
                # More negative max debt means more spending capacity.
                capacity = max(0.0, before_value - after_value)
                self._record_positive(DEBT_CAPACITY, capacity, magnitudes)
                evidence.add(f"context:max_debt:capacity:{capacity:g}")
            handled.add("max_debt")

        for key in ("planet_cards_free", "celestial_packs_free"):
            if changed(key) and after.get(key):
                self._record_positive(SHOP_DISCOUNT, 1.0, magnitudes)
                evidence.add(f"context:{key}")
                handled.add(key)

        internal = {
            "consumable_slots_full",
            "hand_full",
            "boss_blind",
            "deck",
            "deck_target_size",
            "consumables",
            "owned_cards",
            "probability",
            "hands_remaining",
        }
        for key, value in after.items():
            if key in handled or key in internal or not changed(key):
                continue
            if value in (None, False, 0, "", [], {}, ()):
                continue
            magnitudes[f"signal:{key}"] = max(magnitudes.get(f"signal:{key}", 0.0), 1.0)
            evidence.add(f"context:{key}")

    @classmethod
    def _consumable_categories(cls, values: object) -> frozenset[str]:
        if not isinstance(values, Iterable) or isinstance(values, (str, bytes, dict)):
            values = [values]
        categories: set[str] = set()
        for value in values:
            if isinstance(value, Consumable):
                category = str(getattr(value, "category", "")).upper()
                if category:
                    categories.add(category)
                continue
            text = str(value).upper()
            for category in ("TAROT", "PLANET", "SPECTRAL"):
                if category in text:
                    categories.add(category)
        return frozenset(categories)

    @staticmethod
    def _number(value: object) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @classmethod
    def _positive_amount(cls, value: object) -> float:
        number = cls._number(value)
        if number is not None:
            return max(1.0, abs(number))
        return cls._collection_amount(value)

    @staticmethod
    def _collection_amount(value: object) -> float:
        if isinstance(value, (str, bytes, dict)):
            return 1.0
        try:
            return max(1.0, float(len(value)))
        except (TypeError, ValueError):
            return 1.0

    @staticmethod
    def _record_positive(feature: str, amount: float, magnitudes: dict[str, float]) -> None:
        if amount > 0.0:
            magnitudes[feature] = max(magnitudes.get(feature, 0.0), float(amount))

    @staticmethod
    def _record_signed(
        feature: str,
        delta: float,
        magnitudes: dict[str, float],
        penalties: dict[str, float],
    ) -> None:
        if delta > 0.0:
            magnitudes[feature] = max(magnitudes.get(feature, 0.0), float(delta))
        elif delta < 0.0:
            penalties[feature] = max(penalties.get(feature, 0.0), abs(float(delta)))
