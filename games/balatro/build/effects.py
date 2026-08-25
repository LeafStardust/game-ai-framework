from __future__ import annotations

import copy
import random
from dataclasses import dataclass

from games.balatro.card import BalatroCard, ENHANCEMENTS, SEALS
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
    seal, and poker-hand probes vary public conditions so contextual requirements
    can be discovered without maintaining a duplicate pairwise synergy table.
    When a hand-type condition activates an effect, a second conditioned pass
    varies card features while keeping that hand condition fixed; this exposes
    conjunctions such as ``Straight AND Ace`` conservatively.

    Joker scoring is phase-aware in the production model. Synthetic discovery
    therefore probes the neutral semantic fallback and the public scoring phases
    rather than assuming every Joker activates at ``HAND_SCORED``.
    """

    RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    SUITS = ("Hearts", "Diamonds", "Clubs", "Spades")
    HANDS = tuple(PokerHand)

    # Concrete representatives are required here.  Passing a HIGH_CARD card set
    # with a different ``poker_hand`` label misses Jokers that correctly inspect
    # the cards through HandEvaluator.contains (Zany, Crazy, Crafty, etc.).
    _HAND_RANKS: dict[PokerHand, tuple[str, ...]] = {
        PokerHand.HIGH_CARD: ("A", "Q", "J", "9", "2"),
        PokerHand.PAIR: ("8", "8", "K", "7", "2"),
        PokerHand.TWO_PAIR: ("A", "A", "K", "K", "2"),
        PokerHand.THREE_OF_A_KIND: ("Q", "Q", "Q", "7", "2"),
        PokerHand.STRAIGHT: ("10", "J", "Q", "K", "A"),
        PokerHand.FLUSH: ("A", "10", "8", "5", "2"),
        PokerHand.FULL_HOUSE: ("K", "K", "K", "8", "8"),
        PokerHand.FOUR_OF_A_KIND: ("8", "8", "8", "8", "A"),
        PokerHand.STRAIGHT_FLUSH: ("10", "J", "Q", "K", "A"),
        PokerHand.FIVE_OF_A_KIND: ("7", "7", "7", "7", "7"),
        PokerHand.FLUSH_HOUSE: ("K", "K", "K", "8", "8"),
        PokerHand.FLUSH_FIVE: ("7", "7", "7", "7", "7"),
    }
    _FLUSH_HANDS = frozenset(
        {
            PokerHand.FLUSH,
            PokerHand.STRAIGHT_FLUSH,
            PokerHand.FLUSH_HOUSE,
            PokerHand.FLUSH_FIVE,
        }
    )
    _HAND_SUPERSETS: dict[PokerHand, frozenset[PokerHand]] = {
        PokerHand.HIGH_CARD: frozenset(PokerHand),
        PokerHand.PAIR: frozenset(
            {
                PokerHand.TWO_PAIR,
                PokerHand.THREE_OF_A_KIND,
                PokerHand.FULL_HOUSE,
                PokerHand.FOUR_OF_A_KIND,
                PokerHand.FIVE_OF_A_KIND,
                PokerHand.FLUSH_HOUSE,
                PokerHand.FLUSH_FIVE,
            }
        ),
        PokerHand.TWO_PAIR: frozenset({PokerHand.FULL_HOUSE, PokerHand.FLUSH_HOUSE}),
        PokerHand.THREE_OF_A_KIND: frozenset(
            {
                PokerHand.FULL_HOUSE,
                PokerHand.FOUR_OF_A_KIND,
                PokerHand.FIVE_OF_A_KIND,
                PokerHand.FLUSH_HOUSE,
                PokerHand.FLUSH_FIVE,
            }
        ),
        PokerHand.STRAIGHT: frozenset({PokerHand.STRAIGHT_FLUSH}),
        PokerHand.FLUSH: frozenset(
            {PokerHand.STRAIGHT_FLUSH, PokerHand.FLUSH_HOUSE, PokerHand.FLUSH_FIVE}
        ),
        PokerHand.FULL_HOUSE: frozenset({PokerHand.FLUSH_HOUSE}),
        PokerHand.FOUR_OF_A_KIND: frozenset(
            {PokerHand.FIVE_OF_A_KIND, PokerHand.FLUSH_FIVE}
        ),
        PokerHand.FIVE_OF_A_KIND: frozenset({PokerHand.FLUSH_FIVE}),
    }

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

        def record(result: _ProbeResult) -> None:
            results.append(result)
            evidence.update(result.evidence)
            amplifies.update(result.amplifies)

        def compare(feature: str, result: _ProbeResult) -> bool:
            record(result)
            all_outputs = baseline.produced | result.produced
            increased = any(
                result.magnitude(output) > baseline.magnitude(output) + 1e-12
                for output in all_outputs
            )
            if not increased:
                return False
            scales_with.add(feature)
            if any(
                baseline.magnitude(output) <= 1e-12
                and result.magnitude(output) > 1e-12
                for output in all_outputs
            ):
                requires.add(feature)
            return True

        def compare_variants(
            variants: list[tuple[str, _ProbeResult]],
        ) -> None:
            """Infer positive dependencies within one already-active condition."""

            if len(variants) < 2:
                return
            for _, result in variants:
                record(result)

            all_outputs = frozenset(
                output
                for _, result in variants
                for output in result.produced
            )
            for output in all_outputs:
                magnitudes = [result.magnitude(output) for _, result in variants]
                minimum = min(magnitudes)
                maximum = max(magnitudes)
                if maximum <= minimum + 1e-12:
                    continue
                for feature, result in variants:
                    magnitude = result.magnitude(output)
                    if magnitude <= minimum + 1e-12:
                        continue
                    scales_with.add(feature)
                    if minimum <= 1e-12:
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

        active_hand_results: dict[PokerHand, _ProbeResult] = {}
        for poker_hand in self.HANDS:
            hand_cards = self._hand_cards(poker_hand)
            result = self._probe(
                joker,
                cards=hand_cards,
                held_cards=baseline_cards,
                poker_hand=poker_hand,
            )
            if compare(hand_feature(poker_hand), result):
                active_hand_results[poker_hand] = result

        active_hands = self._minimal_active_hands(active_hand_results)
        removed_hands = set(active_hand_results).difference(active_hands)
        requires.difference_update(hand_feature(hand) for hand in removed_hands)
        scales_with.difference_update(hand_feature(hand) for hand in removed_hands)

        for poker_hand in active_hands:
            compare_variants(
                [
                    (
                        rank_feature(rank),
                        self._probe(
                            joker,
                            cards=self._conditioned_rank_cards(poker_hand, rank),
                            held_cards=baseline_cards,
                            poker_hand=poker_hand,
                        ),
                    )
                    for rank in self.RANKS
                ]
            )
            compare_variants(
                [
                    (
                        rank_feature(rank, held=True),
                        self._probe(
                            joker,
                            cards=baseline_cards,
                            held_cards=self._rank_cards(rank),
                            poker_hand=poker_hand,
                        ),
                    )
                    for rank in self.RANKS
                ]
            )
            compare_variants(
                [
                    (
                        suit_feature(suit),
                        self._probe(
                            joker,
                            cards=self._suit_cards(suit),
                            held_cards=baseline_cards,
                            poker_hand=poker_hand,
                        ),
                    )
                    for suit in self.SUITS
                ]
            )
            compare_variants(
                [
                    (
                        suit_feature(suit, held=True),
                        self._probe(
                            joker,
                            cards=baseline_cards,
                            held_cards=self._suit_cards(suit),
                            poker_hand=poker_hand,
                        ),
                    )
                    for suit in self.SUITS
                ]
            )
            compare_variants(
                [
                    (
                        enhancement_feature(enhancement),
                        self._probe(
                            joker,
                            cards=self._enhanced_cards(enhancement),
                            held_cards=baseline_cards,
                            poker_hand=poker_hand,
                        ),
                    )
                    for enhancement in sorted(ENHANCEMENTS)
                ]
            )
            compare_variants(
                [
                    (
                        enhancement_feature(enhancement, held=True),
                        self._probe(
                            joker,
                            cards=baseline_cards,
                            held_cards=self._enhanced_cards(enhancement),
                            poker_hand=poker_hand,
                        ),
                    )
                    for enhancement in sorted(ENHANCEMENTS)
                ]
            )
            compare_variants(
                [
                    (
                        seal_feature(seal),
                        self._probe(
                            joker,
                            cards=self._sealed_cards(seal),
                            held_cards=baseline_cards,
                            poker_hand=poker_hand,
                        ),
                    )
                    for seal in sorted(SEALS)
                ]
            )
            compare_variants(
                [
                    (
                        seal_feature(seal, held=True),
                        self._probe(
                            joker,
                            cards=baseline_cards,
                            held_cards=self._sealed_cards(seal),
                            poker_hand=poker_hand,
                        ),
                    )
                    for seal in sorted(SEALS)
                ]
            )

        # A probe family activating for every possible rank/suit is not evidence
        # that the Joker requires thirteen ranks (or all four suits).  It normally
        # means the synthetic family changed the poker-hand shape: five identical
        # ranks form a kind and five identical suits form a flush.  Keeping those
        # features made conditional hand Jokers look universally compatible and
        # grossly inflated their shop value.
        self._discard_ubiquitous_family(
            requires,
            scales_with,
            (rank_feature(rank) for rank in self.RANKS),
        )
        self._discard_ubiquitous_family(
            requires,
            scales_with,
            (suit_feature(suit) for suit in self.SUITS),
        )

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
        probes = [
            self._probe_trigger(
                joker,
                cards=cards,
                held_cards=held_cards,
                poker_hand=poker_hand,
                trigger="",
            ),
            self._probe_trigger(
                joker,
                cards=cards,
                held_cards=held_cards,
                poker_hand=poker_hand,
                trigger="HAND_SCORED",
            ),
            self._probe_trigger(
                joker,
                cards=cards,
                held_cards=held_cards,
                poker_hand=poker_hand,
                trigger="HAND_PLAYED",
            ),
        ]
        probes.extend(
            self._probe_trigger(
                joker,
                cards=cards,
                held_cards=held_cards,
                poker_hand=poker_hand,
                trigger="PLAYED_CARD",
                data={"played_card": copy.deepcopy(card)},
            )
            for card in cards
        )
        probes.extend(
            self._probe_trigger(
                joker,
                cards=cards,
                held_cards=held_cards,
                poker_hand=poker_hand,
                trigger="HELD_CARD",
                data={"held_card": copy.deepcopy(card)},
            )
            for card in held_cards
        )

        magnitudes: dict[str, float] = {}
        evidence: set[str] = set()
        amplifies: set[str] = set()
        for result in probes:
            evidence.update(result.evidence)
            amplifies.update(result.amplifies)
            for feature, amount in result.magnitudes:
                magnitudes[feature] = max(magnitudes.get(feature, 0.0), amount)
        return _ProbeResult(
            magnitudes=tuple(sorted(magnitudes.items())),
            evidence=tuple(sorted(evidence)),
            amplifies=frozenset(amplifies),
        )

    @staticmethod
    def _probe_trigger(
        joker: Joker,
        *,
        cards: list[BalatroCard],
        held_cards: list[BalatroCard],
        poker_hand: PokerHand,
        trigger: str,
        data: dict | None = None,
    ) -> _ProbeResult:
        state = BalatroState()
        state.hand = copy.deepcopy(cards)
        initial_money = float(state.money)
        score = HandScore(100, 10, 1.0)
        context = JokerContext(
            state=state,
            score=score,
            poker_hand=poker_hand,
            cards=copy.deepcopy(cards),
            held_cards=copy.deepcopy(held_cards),
            trigger=trigger,
            data=copy.deepcopy(data or {}),
        )
        random_state = random.getstate()
        try:
            random.seed(0)
            result = copy.deepcopy(joker).apply(context)
        except (AttributeError, ImportError, KeyError, TypeError, ValueError, ZeroDivisionError):
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

        money_after = float(getattr(result.state, "money", initial_money))
        if money_after != initial_money:
            magnitudes[ECONOMY] = abs(money_after - initial_money)

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

    @classmethod
    def _hand_cards(cls, poker_hand: PokerHand) -> list[BalatroCard]:
        ranks = cls._HAND_RANKS[poker_hand]
        if poker_hand in cls._FLUSH_HANDS:
            suits = ("Hearts",) * len(ranks)
        else:
            suits = tuple(cls.SUITS[index % len(cls.SUITS)] for index in range(len(ranks)))
        return [BalatroCard(rank, suit) for rank, suit in zip(ranks, suits)]

    @classmethod
    def _conditioned_rank_cards(
        cls,
        poker_hand: PokerHand,
        rank: str,
    ) -> list[BalatroCard]:
        """Hold the classified-hand probe constant while varying its rank signal.

        Kind hands remain valid with repeated ranks.  Straight-aware Jokers may use
        the analyzer's authoritative classified-hand fallback so a conjunction such
        as ``Straight AND Ace`` can be isolated without crediting 10/J/Q/K merely
        because they share the same concrete straight.  Other hands retain their
        representative cards.
        """
        if poker_hand in {
            PokerHand.PAIR,
            PokerHand.THREE_OF_A_KIND,
            PokerHand.FOUR_OF_A_KIND,
            PokerHand.FIVE_OF_A_KIND,
            PokerHand.FLUSH_FIVE,
            PokerHand.STRAIGHT,
            PokerHand.STRAIGHT_FLUSH,
        }:
            # The authoritative classified-hand fallback intentionally isolates a
            # rank conjunction here.  A real straight containing Ace also contains
            # 10/J/Q/K, so sliding real straight windows would falsely attribute
            # Superposition's Ace requirement to all five ranks.
            return cls._rank_cards(rank)

        return cls._hand_cards(poker_hand)

    @staticmethod
    def _discard_ubiquitous_family(
        requires: set[str],
        scales_with: set[str],
        features,
    ) -> None:
        family = set(features)
        if family and family.issubset(scales_with):
            scales_with.difference_update(family)
            requires.difference_update(family)

    @classmethod
    def _minimal_active_hands(
        cls,
        active: dict[PokerHand, _ProbeResult],
    ) -> list[PokerHand]:
        """Remove hand labels explained entirely by a weaker contains-condition."""
        retained: list[PokerHand] = []
        for hand in active:
            result = active[hand]
            redundant = False
            for base, base_result in active.items():
                if hand not in cls._HAND_SUPERSETS.get(base, frozenset()):
                    continue
                outputs = result.produced | base_result.produced
                if all(
                    result.magnitude(output) <= base_result.magnitude(output) + 1e-12
                    for output in outputs
                ):
                    redundant = True
                    break
            if not redundant:
                retained.append(hand)
        return retained

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

        if len(before.hand) == len(result.state.hand):
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
