from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from games.balatro.state import BalatroState

from .effects import (
    HELD_EFFECT,
    ConsumableBehaviorAnalyzer,
    EffectDescriptor,
    JokerBehaviorAnalyzer,
    consumable_category_feature,
    describe_build_item,
    edition_feature,
    enhancement_feature,
    hand_feature,
    rank_feature,
    seal_feature,
    suit_feature,
)
from .joker_scenarios import ScenarioJokerBehaviorAnalyzer


@dataclass(frozen=True)
class BuildProfile:
    """Order-independent public description of the current Balatro build.

    ``feature_strengths`` represents effects that are already active/realized in
    the current build (deck composition, hand-level investment, owned Jokers).
    Held consumables remain descriptors in ``effects`` so future synergy evaluation
    can reason about what they can create without pretending that transformation has
    already happened.

    Strategic direction is intentionally absent from this data model. Canonical
    Bonds/composition derive strategy from the same public mechanics without a
    second categorical intent vector or an irreversible Ante lock.
    """

    money: int
    ante: int
    joker_slots: int
    free_joker_slots: int
    consumable_slots: int
    free_consumable_slots: int
    deck_size: int
    rank_counts: tuple[tuple[str, int], ...]
    suit_counts: tuple[tuple[str, int], ...]
    enhancement_counts: tuple[tuple[str, int], ...]
    seal_counts: tuple[tuple[str, int], ...]
    edition_counts: tuple[tuple[str, int], ...]
    hand_levels: tuple[tuple[str, int], ...]
    joker_names: tuple[str, ...]
    consumable_names: tuple[str, ...]
    effects: tuple[EffectDescriptor, ...]
    feature_strengths: tuple[tuple[str, float], ...]

    def strength(self, feature: str) -> float:
        return dict(self.feature_strengths).get(feature, 0.0)

    def supports(self, feature: str) -> bool:
        return self.strength(feature) > 0.0

    def can_produce(self, feature: str) -> bool:
        return any(descriptor.supports(feature) for descriptor in self.effects)

    def amplifies(self, feature: str) -> bool:
        return any(feature in descriptor.amplifies for descriptor in self.effects)

    def descriptors(self, *, kind: str | None = None) -> tuple[EffectDescriptor, ...]:
        if kind is None:
            return self.effects
        return tuple(
            descriptor
            for descriptor in self.effects
            if descriptor.kind == kind
        )


class BalatroBuildProfiler:
    """Derive build context from translated public Balatro state only.

    Card order is intentionally discarded. When authoritative ``state.owned_deck``
    composition is available, permanent build features come from it; older or
    synthetic states that do not expose owned-deck composition fall back to the
    legacy ``state.deck`` field. Neither path asks for hidden draw order or RNG.
    """

    def __init__(
        self,
        *,
        joker_analyzer: JokerBehaviorAnalyzer | None = None,
        consumable_analyzer: ConsumableBehaviorAnalyzer | None = None,
    ) -> None:
        self.joker_analyzer = joker_analyzer or ScenarioJokerBehaviorAnalyzer()
        self.consumable_analyzer = consumable_analyzer or ConsumableBehaviorAnalyzer()

    def profile(self, state: BalatroState) -> BuildProfile:
        owned_deck = getattr(state, "owned_deck", None)
        deck = list(
            owned_deck
            if owned_deck is not None
            else getattr(state, "deck", ())
        )
        rank_counts: Counter[str] = Counter()
        suit_counts: Counter[str] = Counter()
        enhancement_counts: Counter[str] = Counter()
        seal_counts: Counter[str] = Counter()
        edition_counts: Counter[str] = Counter()
        strengths: Counter[str] = Counter()

        for card in deck:
            rank = getattr(card, "rank", None)
            suit = getattr(card, "suit", None)
            enhancement = getattr(card, "enhancement", None)
            seal = getattr(card, "seal", None)
            edition = getattr(card, "edition", None)

            if rank is not None and enhancement != "Stone":
                rank_counts[str(rank)] += 1
                strengths[rank_feature(str(rank))] += 1.0
            if suit is not None and enhancement != "Stone":
                suit_counts[str(suit)] += 1
                strengths[suit_feature(str(suit))] += 1.0
            if enhancement:
                enhancement_counts[str(enhancement)] += 1
                strengths[enhancement_feature(str(enhancement))] += 1.0
            if seal:
                seal_counts[str(seal)] += 1
                strengths[seal_feature(str(seal))] += 1.0
            if edition:
                edition_counts[str(edition)] += 1
                strengths[edition_feature(str(edition))] += 1.0

            # These card properties already have meaningful held-card behavior in
            # the modeled game. Count the source potential without assuming which
            # cards will be drawn or held in a future hand.
            if enhancement in {"Steel", "Gold"} or seal == "Blue":
                strengths[HELD_EFFECT] += 1.0

        hand_levels = {
            str(hand): int(level)
            for hand, level in getattr(state, "hand_levels", {}).items()
        }
        for hand, level in hand_levels.items():
            # Every ordinary poker hand begins at level 1. That universal baseline
            # is a game rule, not evidence that the current build is specialized in
            # every hand type. Only investment above level 1 contributes contextual
            # build strength; the exact raw level remains available in hand_levels.
            investment = max(0.0, float(level) - 1.0)
            if investment > 0.0:
                strengths[hand_feature(hand)] += investment

        effects: list[EffectDescriptor] = []
        joker_names: list[str] = []
        for joker in getattr(state, "jokers", ()):
            descriptor = describe_build_item(
                joker,
                state=state,
                joker_analyzer=self.joker_analyzer,
                consumable_analyzer=self.consumable_analyzer,
            )
            effects.append(descriptor)
            joker_names.append(type(joker).__name__)
            # Owned Jokers are active build components, so their observable outputs
            # belong to current strengths. Requirements are kept separate.
            for feature in descriptor.produces:
                strengths[feature] += 1.0

        consumable_names: list[str] = []
        for consumable in getattr(state, "consumables", ()):
            descriptor = describe_build_item(
                consumable,
                state=state,
                joker_analyzer=self.joker_analyzer,
                consumable_analyzer=self.consumable_analyzer,
            )
            effects.append(descriptor)
            consumable_names.append(
                str(getattr(consumable, "name", type(consumable).__name__))
            )
            category = str(getattr(consumable, "category", "")).upper()
            if category:
                # Inventory availability is active information; downstream
                # transformation/score outputs remain prospective in descriptor.
                strengths[consumable_category_feature(category)] += 1.0

        joker_slots = int(getattr(state, "joker_slots", 0))
        consumable_slots = int(getattr(state, "consumable_slots", 0))
        return BuildProfile(
            money=int(getattr(state, "money", 0)),
            ante=int(getattr(state, "ante", 0)),
            joker_slots=joker_slots,
            free_joker_slots=max(0, joker_slots - len(getattr(state, "jokers", ()))),
            consumable_slots=consumable_slots,
            free_consumable_slots=max(
                0,
                consumable_slots - len(getattr(state, "consumables", ())),
            ),
            deck_size=len(deck),
            rank_counts=tuple(sorted(rank_counts.items())),
            suit_counts=tuple(sorted(suit_counts.items())),
            enhancement_counts=tuple(sorted(enhancement_counts.items())),
            seal_counts=tuple(sorted(seal_counts.items())),
            edition_counts=tuple(sorted(edition_counts.items())),
            hand_levels=tuple(sorted(hand_levels.items())),
            joker_names=tuple(joker_names),
            consumable_names=tuple(consumable_names),
            effects=tuple(effects),
            feature_strengths=tuple(sorted(strengths.items())),
        )
