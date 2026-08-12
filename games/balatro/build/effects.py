from __future__ import annotations

import copy
import random
from dataclasses import dataclass

from games.balatro.card import BalatroCard, EDITIONS, ENHANCEMENTS, SEALS
from games.balatro.consumable import Consumable, ConsumableContext, PlanetCard
from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext
from games.balatro.scoring import HandScore
from games.balatro.state import BalatroState


SCORE_CHIPS = "score:chips"
SCORE_MULT = "score:mult"
SCORE_XMULT = "score:x_mult"
HELD_EFFECT = "held:effect"
HELD_RETRIGGER = "held:retrigger"
ECONOMY = "economy"
HAND_LEVEL = "hand_level"
DECK_TRANSFORM = "deck:transform"
DECK_REMOVE = "deck:remove"
JOKER_GENERATE = "joker:generate"
CONSUMABLE_GENERATE = "consumable:generate"
TARGET_CARD = "target:card"


def rank_feature(rank: str, *, held: bool = False) -> str:
    prefix = "held:rank" if held else "rank"
    return f"{prefix}:{rank}"


def suit_feature(suit: str, *, held: bool = False) -> str:
    prefix = "held:suit" if held else "suit"
    return f"{prefix}:{suit}"


def enhancement_feature(enhancement: str, *, held: bool = False) -> str:
    prefix = "held:enhancement" if held else "enhancement"
    return f"{prefix}:{enhancement}"


def seal_feature(seal: str, *, held: bool = False) -> str:
    prefix = "held:seal" if held else "seal"
    return f"{prefix}:{seal}"


def edition_feature(edition: str) -> str:
    return f"edition:{edition}"


def hand_feature(hand_type: object) -> str:
    value = getattr(hand_type, "value", hand_type)
    return f"hand:{value}"


def consumable_category_feature(category: str) -> str:
    return f"consumable:{str(category).upper()}"


@dataclass(frozen=True)
class EffectDescriptor:
    """Behavior-backed vocabulary used to reason about Balatro build synergies.

    The descriptor is deliberately compositional rather than a tier/rating table.
    ``produces`` records observable outputs, ``requires`` and ``scales_with``
    record conditions that changed those outputs in controlled probes,
    ``amplifies`` records known effect-to-effect interactions, and ``transforms``
    records persistent card/build transformations.

    Unknown behavior stays absent. ``evidence`` may retain raw observable signals
    without promoting them into unsupported strategic semantics.
    """

    source: str
    kind: str
    produces: frozenset[str] = frozenset()
    requires: frozenset[str] = frozenset()
    amplifies: frozenset[str] = frozenset()
    scales_with: frozenset[str] = frozenset()
    transforms: frozenset[str] = frozenset()
    evidence: tuple[str, ...] = ()

    def supports(self, feature: str) -> bool:
        return feature in self.produces or feature in self.transforms


@dataclass(frozen=True)
class _ProbeResult:
    magnitudes: tuple[tuple[str, float], ...] = ()
    evidence: tuple[str, ...] = ()
    amplifies: frozenset[str] = frozenset()

    def magnitude(self, feature: str) -> float:
        return dict(self.magnitudes).get(feature, 0.0)

    @property
    def produced(self) -> frozenset[str]:
        return frozenset(feature for feature, amount in self.magnitudes if amount > 0.0)


class JokerBehaviorAnalyzer:
    """Infer reusable Joker effect semantics by invoking its real implementation.

    Probes operate only on synthetic/deep-copied state. Rank, suit, enhancement,
    seal, and poker-hand probes vary one public condition at a time so contextual
    requirements can be discovered without maintaining a duplicate pairwise
    synergy table. Probe failures remain conservative: no feature is invented.
    """

    RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    SUITS = ("Hearts", "Diamonds", "Clubs", "Spades")
    HANDS = tuple(PokerHand)

    def describe(self, joker: object) -> EffectDescriptor:
        source = type(joker).__name__
        if not isinstance(joker, Joker):
            return EffectDescriptor(source=source, kind="UNKNOWN")

        baseline_cards = self._neutral_cards()
        baseline = self._probe(joker, cards=baseline_cards, held_cards=baseline_cards)
        results = [baseline]
        requires: set[str] = set()
        scales_with: set[str] = set()
        evidence: set[str] = set(baseline.evidence)
        amplifies: set[str] = set(baseline.amplifies)

        def compare(feature: str, result: _ProbeResult) -> None:
            results.append(result)
            evidence.update(result.evidence)
            amplifies.update(result.amplifies)
            all_outputs = baseline.produced | result.produced
            changed = any(
                abs(result.magnitude(output) - baseline.magnitude(output)) > 1e-12
                for output in all_outputs
            )
            if not changed:
                return
            scales_with.add(feature)
            if any(
                baseline.magnitude(output) <= 1e-12
                and result.magnitude(output) > 1e-12
                for output in all_outputs
            ):
                requires.add(feature)

        for rank in self.RANKS:
            compare(
                rank_feature(rank),
                self._probe(
                    joker,
                    cards=self._rank_cards(rank),
                    held_cards=baseline_cards,
                ),
            )
            compare(
                rank_feature(rank, held=True),
                self._probe(
                    joker,
                    cards=baseline_cards,
                    held_cards=self._rank_cards(rank),
                ),
            )

        for suit in self.SUITS:
            compare(
                suit_feature(suit),
                self._probe(
                    joker,
                    cards=self._suit_cards(suit),
                    held_cards=baseline_cards,
                ),
            )
            compare(
                suit_feature(suit, held=True),
                self._probe(
                    joker,
                    cards=baseline_cards,
                    held_cards=self._suit_cards(suit),
                ),
            )

        for enhancement in sorted(ENHANCEMENTS):
            compare(
                enhancement_feature(enhancement),
                self._probe(
                    joker,
                    cards=self._enhanced_cards(enhancement),
                    held_cards=baseline_cards,
                ),
            )
            compare(
                enhancement_feature(enhancement, held=True),
                self._probe(
                    joker,
                    cards=baseline_cards,
                    held_cards=self._enhanced_cards(enhancement),
                ),
            )

        for seal in sorted(SEALS):
            compare(
                seal_feature(seal),
                self._probe(
                    joker,
                    cards=self._sealed_cards(seal),
                    held_cards=baseline_cards,
                ),
            )
            compare(
                seal_feature(seal, held=True),
                self._probe(
                    joker,
                    cards=baseline_cards,
                    held_cards=self._sealed_cards(seal),
                ),
            )

        for poker_hand in self.HANDS:
            result = self._probe(
                joker,
                cards=baseline_cards,
                held_cards=baseline_cards,
                poker_hand=poker_hand,
            )
            compare(hand_feature(poker_hand), result)

        produced = frozenset(
            feature
            for result in results
            for feature in result.produced
        )
        return EffectDescriptor(
            source=source,
            kind="JOKER",
            produces=produced,
            requires=frozenset(requires),
            amplifies=frozenset(amplifies),
            scales_with=frozenset(scales_with),
            evidence=tuple(sorted(evidence)),
        )

    def _probe(
        self,
        joker: Joker,
        *,
        cards: list[BalatroCard],
        held_cards: list[BalatroCard],
        poker_hand: PokerHand = PokerHand.HIGH_CARD,
    ) -> _ProbeResult:
        state = BalatroState()
        state.hand = copy.deepcopy(cards)
        score = HandScore(100, 10, 1.0)
        context = JokerContext(
            state=state,
            score=score,
            poker_hand=poker_hand,
            cards=copy.deepcopy(cards),
            held_cards=copy.deepcopy(held_cards),
            trigger="HAND_SCORED",
            data={},
        )
        random_state = random.getstate()
        try:
            random.seed(0)
            result = copy.deepcopy(joker).apply(context)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return _ProbeResult()
        finally:
            random.setstate(random_state)

        score_after = getattr(result, "score", None)
        magnitudes: dict[str, float] = {}
        if score_after is not None:
            if score_after.chips != 100:
                magnitudes[SCORE_CHIPS] = abs(float(score_after.chips) - 100.0)
            if score_after.mult != 10:
                magnitudes[SCORE_MULT] = abs(float(score_after.mult) - 10.0)
            if abs(float(score_after.x_mult) - 1.0) > 1e-12:
                magnitudes[SCORE_XMULT] = abs(float(score_after.x_mult) - 1.0)

        evidence: set[str] = set()
        amplifies: set[str] = set()
        for key, value in (getattr(result, "data", {}) or {}).items():
            if value in (None, False, 0, "", [], {}, ()):
                continue
            signal = str(key)
            evidence.add(f"context:{signal}")
            if signal == "retrigger_held_abilities":
                amount = float(value) if isinstance(value, (int, float)) else 1.0
                magnitudes[HELD_RETRIGGER] = max(1.0, abs(amount))
                amplifies.add(HELD_EFFECT)
            else:
                magnitudes[f"signal:{signal}"] = 1.0

        if getattr(result.state, "money", 0) != state.money:
            magnitudes[ECONOMY] = abs(float(result.state.money) - float(state.money))

        return _ProbeResult(
            magnitudes=tuple(sorted(magnitudes.items())),
            evidence=tuple(sorted(evidence)),
            amplifies=frozenset(amplifies),
        )

    @staticmethod
    def _neutral_cards() -> list[BalatroCard]:
        return [
            BalatroCard("A", "Spades"),
            BalatroCard("Q", "Hearts"),
            BalatroCard("J", "Clubs"),
            BalatroCard("9", "Diamonds"),
            BalatroCard("2", "Spades"),
        ]

    @classmethod
    def _rank_cards(cls, rank: str) -> list[BalatroCard]:
        suits = cls.SUITS
        return [BalatroCard(rank, suits[index % len(suits)]) for index in range(5)]

    @staticmethod
    def _suit_cards(suit: str) -> list[BalatroCard]:
        return [BalatroCard(rank, suit) for rank in ("A", "Q", "J", "9", "2")]

    @classmethod
    def _enhanced_cards(cls, enhancement: str) -> list[BalatroCard]:
        cards = cls._neutral_cards()
        for card in cards:
            card.enhancement = enhancement
        return cards

    @classmethod
    def _sealed_cards(cls, seal: str) -> list[BalatroCard]:
        cards = cls._neutral_cards()
        for card in cards:
            card.seal = seal
        return cards


class ConsumableBehaviorAnalyzer:
    """Describe modeled consumables by applying their real use implementation.

    Deterministic state/card transformations are inferred from copied state. Items
    that need unavailable runtime callbacks or random providers simply retain only
    their known category; the analyzer never fabricates their downstream effect.
    """

    def describe(
        self,
        consumable: object,
        *,
        state: BalatroState | None = None,
    ) -> EffectDescriptor:
        source = str(getattr(consumable, "name", type(consumable).__name__))
        if not isinstance(consumable, Consumable):
            return EffectDescriptor(source=source, kind="UNKNOWN")

        category = str(getattr(consumable, "category", "")).upper()
        produces: set[str] = {consumable_category_feature(category)} if category else set()
        requires: set[str] = set()
        transforms: set[str] = set()
        evidence: set[str] = set()

        if isinstance(consumable, PlanetCard):
            produces.update(
                {
                    HAND_LEVEL,
                    hand_feature(consumable.hand_type),
                    SCORE_CHIPS,
                    SCORE_MULT,
                }
            )
            evidence.add(
                f"planet:{consumable.hand_type}:+{consumable.chips}chips:+{consumable.mult}mult"
            )
            return EffectDescriptor(
                source=source,
                kind="CONSUMABLE",
                produces=frozenset(produces),
                evidence=tuple(sorted(evidence)),
            )

        before = copy.deepcopy(state) if state is not None else self._probe_state()
        if not before.hand:
            before.hand = self._probe_state().hand
        working = copy.deepcopy(before)
        item = copy.deepcopy(consumable)

        try:
            options = item.get_target_cards(working)
        except (AttributeError, KeyError, TypeError, ValueError):
            options = [[]]
        selected = next((list(option) for option in options if option), [])
        if selected:
            requires.add(TARGET_CARD)

        context = ConsumableContext(
            state=working,
            cards=selected,
            data={"rng": random.Random(0)},
        )
        try:
            if not item.can_use(context):
                return EffectDescriptor(
                    source=source,
                    kind="CONSUMABLE",
                    produces=frozenset(produces),
                    requires=frozenset(requires),
                )
            result = item.use(context)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return EffectDescriptor(
                source=source,
                kind="CONSUMABLE",
                produces=frozenset(produces),
                requires=frozenset(requires),
            )

        if result.state.money != before.money:
            produces.add(ECONOMY)
            evidence.add(f"money:{before.money}->{result.state.money}")

        for hand_type, level in result.state.hand_levels.items():
            before_level = before.hand_levels.get(hand_type)
            if before_level is not None and level != before_level:
                produces.update({HAND_LEVEL, hand_feature(hand_type)})
                evidence.add(f"hand_level:{hand_type}:{before_level}->{level}")

        for before_card, after_card in zip(before.hand, result.state.hand):
            if before_card.rank != after_card.rank:
                feature = rank_feature(after_card.rank)
                transforms.add(feature)
                evidence.add(f"rank:{before_card.rank}->{after_card.rank}")
            if before_card.suit != after_card.suit:
                feature = suit_feature(after_card.suit)
                transforms.add(feature)
                evidence.add(f"suit:{before_card.suit}->{after_card.suit}")
            if before_card.enhancement != after_card.enhancement and after_card.enhancement:
                feature = enhancement_feature(after_card.enhancement)
                transforms.add(feature)
                evidence.add(
                    f"enhancement:{before_card.enhancement}->{after_card.enhancement}"
                )
            if before_card.edition != after_card.edition and after_card.edition:
                feature = edition_feature(after_card.edition)
                transforms.add(feature)
                evidence.add(f"edition:{before_card.edition}->{after_card.edition}")
            if before_card.seal != after_card.seal and after_card.seal:
                feature = seal_feature(after_card.seal)
                transforms.add(feature)
                evidence.add(f"seal:{before_card.seal}->{after_card.seal}")

        if transforms:
            produces.add(DECK_TRANSFORM)
            produces.update(transforms)

        data = getattr(result, "data", {}) or {}
        if data.get("create_joker"):
            produces.add(JOKER_GENERATE)
        created = data.get("created")
        if created:
            produces.add(CONSUMABLE_GENERATE)
            for created_item in created:
                created_category = str(getattr(created_item, "category", "")).upper()
                if created_category:
                    produces.add(consumable_category_feature(created_category))
        if data.get("destroyed"):
            produces.add(DECK_REMOVE)

        evidence.update(
            f"context:{key}"
            for key, value in data.items()
            if value not in (None, False, 0, "", [], {}, ())
        )

        return EffectDescriptor(
            source=source,
            kind="CONSUMABLE",
            produces=frozenset(produces),
            requires=frozenset(requires),
            transforms=frozenset(transforms),
            evidence=tuple(sorted(evidence)),
        )

    @staticmethod
    def _probe_state() -> BalatroState:
        state = BalatroState()
        state.money = 10
        state.hand = [
            BalatroCard("A", "Spades"),
            BalatroCard("K", "Hearts"),
            BalatroCard("9", "Clubs"),
        ]
        return state


def describe_build_item(
    item: object,
    *,
    state: BalatroState | None = None,
    joker_analyzer: JokerBehaviorAnalyzer | None = None,
    consumable_analyzer: ConsumableBehaviorAnalyzer | None = None,
) -> EffectDescriptor:
    if isinstance(item, Joker):
        return (joker_analyzer or JokerBehaviorAnalyzer()).describe(item)
    if isinstance(item, Consumable):
        return (consumable_analyzer or ConsumableBehaviorAnalyzer()).describe(
            item,
            state=state,
        )
    return EffectDescriptor(source=type(item).__name__, kind="UNKNOWN")
