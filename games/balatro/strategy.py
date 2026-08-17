from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Mapping

GOLD = "GOLD"
SILVER = "SILVER"
BRONZE = "BRONZE"
NEUTRAL = "NEUTRAL"
BANNED = "BANNED"

AVAILABLE = "AVAILABLE"
CANDIDATE = "CANDIDATE"
HIGHLIGHTED = "HIGHLIGHTED"
COMMITTED = "COMMITTED"
MATURE = "MATURE"

_DEFAULT_RELATIONSHIP_SCORE = {
    GOLD: 5.0,
    SILVER: 3.0,
    BRONZE: 1.0,
    NEUTRAL: 0.0,
    BANNED: -8.0,
}
_RELATIONSHIP_PRIORITY = {
    BANNED: 4,
    GOLD: 3,
    SILVER: 2,
    BRONZE: 1,
    NEUTRAL: 0,
}
_POSITIVE_RELATIONSHIP_PRIORITY = {
    GOLD: 3,
    SILVER: 2,
    BRONZE: 1,
    BANNED: 0,
    NEUTRAL: 0,
}


def _normalize(value: object) -> str:
    return "".join(c for c in str(value).lower() if c.isalnum())


def _tokens(item: object) -> frozenset[str]:
    values = (
        type(item).__name__,
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "key", ""),
        getattr(item, "center", ""),
    )
    return frozenset(token for value in values if (token := _normalize(value)))


@dataclass(frozen=True)
class StrategyDefinition:
    """Universal Balatro strategy knowledge.

    Deck/stake cartridges may change feasibility/effectiveness/base bias, but they
    never redefine these component relationships.
    """

    strategy_id: str
    name: str
    primary_hands: tuple[str, ...] = ()

    gold_jokers: frozenset[str] = frozenset()
    silver_jokers: frozenset[str] = frozenset()
    bronze_jokers: frozenset[str] = frozenset()
    banned_jokers: frozenset[str] = frozenset()

    gold_consumables: frozenset[str] = frozenset()
    silver_consumables: frozenset[str] = frozenset()
    bronze_consumables: frozenset[str] = frozenset()
    banned_consumables: frozenset[str] = frozenset()

    gold_planets: frozenset[str] = frozenset()
    silver_planets: frozenset[str] = frozenset()
    bronze_planets: frozenset[str] = frozenset()
    banned_planets: frozenset[str] = frozenset()

    gold_vouchers: frozenset[str] = frozenset()
    silver_vouchers: frozenset[str] = frozenset()
    bronze_vouchers: frozenset[str] = frozenset()
    banned_vouchers: frozenset[str] = frozenset()

    preferred_suits: tuple[str, ...] = ()
    preferred_enhancements: tuple[str, ...] = ()
    preferred_seals: tuple[str, ...] = ()
    preferred_editions: tuple[str, ...] = ()
    preferred_ranks: tuple[str, ...] = ()
    face_mode: str | None = None
    any_suit_concentration: bool = False

    required_jokers: frozenset[str] = frozenset()
    minimum_positive_jokers: int = 0
    entry_evidence_cap: float = 1.0

    def _buckets(self, kind: str):
        kind = str(kind).upper()
        if kind == "JOKER":
            return (
                (BANNED, self.banned_jokers),
                (GOLD, self.gold_jokers),
                (SILVER, self.silver_jokers),
                (BRONZE, self.bronze_jokers),
            )
        if kind == "PLANET":
            return (
                (BANNED, self.banned_planets),
                (GOLD, self.gold_planets),
                (SILVER, self.silver_planets),
                (BRONZE, self.bronze_planets),
            )
        if kind == "VOUCHER":
            return (
                (BANNED, self.banned_vouchers),
                (GOLD, self.gold_vouchers),
                (SILVER, self.silver_vouchers),
                (BRONZE, self.bronze_vouchers),
            )
        return (
            (BANNED, self.banned_consumables),
            (GOLD, self.gold_consumables),
            (SILVER, self.silver_consumables),
            (BRONZE, self.bronze_consumables),
        )

    def relationship_for(self, item: object, *, kind: str) -> str:
        item_tokens = _tokens(item)
        for relationship, names in self._buckets(kind):
            if item_tokens & names:
                return relationship
        return NEUTRAL

    def tier_for(self, item: object, *, kind: str) -> str | None:
        relationship = self.relationship_for(item, kind=kind)
        return None if relationship == NEUTRAL else relationship

    def conflicts_with(self, item: object, *, kind: str = "JOKER") -> bool:
        return self.relationship_for(item, kind=kind) == BANNED


@dataclass(frozen=True)
class StrategyAssessment:
    strategy_id: str
    name: str
    score: float
    effectiveness: float
    base_score: float
    status: str
    gold_owned: int
    silver_owned: int
    bronze_owned: int
    banned_owned: int
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyResolution:
    dominant_strategy_id: str | None
    relevant_strategy_ids: tuple[str, ...]
    active_strategy_id: str | None
    highlighted_strategy_id: str | None
    committed_strategy_id: str | None
    active_status: str
    assessments: tuple[StrategyAssessment, ...]
    changed: bool = False
    rationale: tuple[str, ...] = ()

    def assessment(self, strategy_id: str | None) -> StrategyAssessment | None:
        return next(
            (a for a in self.assessments if a.strategy_id == strategy_id),
            None,
        )

    @property
    def shortlist_strategy_ids(self) -> tuple[str, ...]:
        if self.dominant_strategy_id is None:
            return self.relevant_strategy_ids
        return (self.dominant_strategy_id, *self.relevant_strategy_ids)


@dataclass(frozen=True)
class StrategicItemEvaluation:
    candidate: str
    kind: str
    strategy_id: str | None
    strategy_name: str | None
    tier: str | None
    value: float
    projected_score: float
    active_alignment: bool
    pivot_candidate: bool
    rationale: tuple[str, ...] = ()


def build_component_strategy_index(
    definitions: Mapping[str, StrategyDefinition],
) -> Mapping[str, Mapping[str, tuple[tuple[str, str], ...]]]:
    """Generate the inverse component -> strategy relationship index once."""

    by_kind: dict[str, dict[str, list[tuple[str, str]]]] = {
        "JOKER": {},
        "CONSUMABLE": {},
        "PLANET": {},
        "VOUCHER": {},
    }
    for strategy_id, definition in definitions.items():
        for kind in by_kind:
            for relationship, names in definition._buckets(kind):
                for name in names:
                    by_kind[kind].setdefault(name, []).append(
                        (strategy_id, relationship)
                    )
    frozen = {
        kind: MappingProxyType(
            {token: tuple(entries) for token, entries in values.items()}
        )
        for kind, values in by_kind.items()
    }
    return MappingProxyType(frozen)


class BalatroStrategyTracker:
    """Current-state universal strategy scoring plus cartridge modifiers."""

    def __init__(
        self,
        definitions: Mapping[str, StrategyDefinition],
        *,
        modifier_provider: Callable[[object], Mapping[str, object]] | None = None,
    ) -> None:
        self.definitions = dict(definitions)
        self.modifier_provider = modifier_provider or (lambda state: {})
        self.component_index = build_component_strategy_index(self.definitions)
        self._last_dominant_strategy_id: str | None = None
        self._last_relevant_strategy_ids: tuple[str, ...] = ()

    def reset(self) -> None:
        self._last_dominant_strategy_id = None
        self._last_relevant_strategy_ids = ()

    def _config(self, state) -> Mapping[str, object]:
        value = self.modifier_provider(state) or {}
        if not isinstance(value, Mapping):
            raise TypeError("strategy modifiers must be a mapping")
        return value

    @staticmethod
    def _number(config: Mapping[str, object], key: str, default: float) -> float:
        try:
            return float(config.get(key, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _modifier(config: Mapping[str, object], strategy_id: str) -> Mapping[str, object]:
        strategies = config.get("strategies", {})
        if not isinstance(strategies, Mapping):
            return {}
        value = strategies.get(strategy_id, {})
        return value if isinstance(value, Mapping) else {}

    def relationship_score(self, state, relationship: str) -> float:
        config = self._config(state)
        defaults = {
            GOLD: self._number(config, "gold_evidence", 5.0),
            SILVER: self._number(config, "silver_evidence", 3.0),
            BRONZE: self._number(config, "bronze_evidence", 1.0),
            NEUTRAL: 0.0,
            BANNED: self._number(config, "banned_evidence", -8.0),
        }
        return defaults.get(relationship, _DEFAULT_RELATIONSHIP_SCORE.get(relationship, 0.0))

    def effectiveness(self, state, strategy_id: str) -> float:
        config = self._config(state)
        modifier = self._modifier(config, strategy_id)
        if modifier.get("enabled", True) is False:
            return 0.0
        try:
            return max(0.0, float(modifier.get("effectiveness", 1.0)))
        except (TypeError, ValueError):
            return 1.0

    def base_strategy_score(self, state, strategy_id: str) -> float:
        config = self._config(state)
        modifier = self._modifier(config, strategy_id)
        value = modifier.get("base_score", modifier.get("score_bonus", 0.0))
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def strategy_pressure(self, state) -> float:
        config = self._config(state)
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante == 1:
            base = self._number(config, "ante_1_strategy_pressure", 0.20)
        elif ante == 2:
            base = self._number(config, "ante_2_strategy_pressure", 0.35)
        elif ante == 3:
            base = self._number(config, "ante_3_strategy_pressure", 0.60)
        elif ante == 4:
            base = self._number(config, "ante_4_strategy_pressure", 0.80)
        elif ante == 5:
            base = self._number(config, "ante_5_strategy_pressure", 1.00)
        else:
            base = min(
                self._number(config, "late_strategy_pressure_cap", 1.50),
                self._number(config, "ante_6_strategy_pressure", 1.25)
                + max(0, ante - 6)
                * self._number(config, "late_strategy_pressure_step", 0.10),
            )
        return max(
            0.0,
            base * self._number(config, "strategy_pressure_multiplier", 1.0),
        )

    def _relationships_for(self, item: object, *, kind: str) -> dict[str, str]:
        kind = str(kind).upper()
        index = self.component_index.get(kind, {})
        found: dict[str, str] = {}
        for token in _tokens(item):
            for strategy_id, relationship in index.get(token, ()):
                previous = found.get(strategy_id, NEUTRAL)
                if _RELATIONSHIP_PRIORITY[relationship] > _RELATIONSHIP_PRIORITY[previous]:
                    found[strategy_id] = relationship
        return found

    @staticmethod
    def _owned_deck(state):
        owned = getattr(state, "owned_deck", None)
        if owned is not None:
            return list(owned)
        return list(getattr(state, "deck", ()) or ())

    @staticmethod
    def _has_joker(state, normalized_names: frozenset[str]) -> bool:
        if not normalized_names:
            return True
        return any(_tokens(joker) & normalized_names for joker in getattr(state, "jokers", ()))

    def _deck_evidence(
        self,
        state,
        definition: StrategyDefinition,
        config: Mapping[str, object],
    ) -> tuple[float, tuple[str, ...]]:
        deck = self._owned_deck(state)
        if not deck:
            return 0.0, ()

        raw = 0.0
        notes: list[str] = []
        non_stone = [card for card in deck if str(getattr(card, "enhancement", "")) != "Stone"]
        total = max(1, len(non_stone))

        if definition.any_suit_concentration and non_stone:
            counts = {
                suit: sum(
                    1
                    for card in non_stone
                    if str(getattr(card, "suit", "")) == suit
                    or str(getattr(card, "enhancement", "")) == "Wild"
                )
                for suit in ("Hearts", "Diamonds", "Clubs", "Spades")
            }
            excess = max(0.0, max(counts.values(), default=0) - total / 4.0)
            if excess:
                gain = excess * self._number(config, "deck_suit_evidence_weight", 0.25)
                raw += gain
                notes.append(f"dominant suit concentration evidence={gain:.3f}")

        if definition.preferred_suits and non_stone:
            preferred = set(definition.preferred_suits)
            smeared = any(
                _normalize(type(joker).__name__) == "smearedjoker"
                for joker in getattr(state, "jokers", ())
            )
            if smeared and len(preferred) == 1:
                target = next(iter(preferred))
                if target in {"Hearts", "Diamonds"}:
                    preferred = {"Hearts", "Diamonds"}
                elif target in {"Clubs", "Spades"}:
                    preferred = {"Clubs", "Spades"}
            matching = sum(
                1
                for card in non_stone
                if str(getattr(card, "suit", "")) in preferred
                or str(getattr(card, "enhancement", "")) == "Wild"
            )
            baseline = total * len(preferred) / 4.0
            excess = max(0.0, matching - baseline)
            if excess:
                gain = excess * self._number(config, "deck_suit_evidence_weight", 0.25)
                raw += gain
                notes.append(f"preferred suit concentration evidence={gain:.3f}")

        if definition.preferred_enhancements:
            matches = sum(
                str(getattr(card, "enhancement", "")) in definition.preferred_enhancements
                for card in deck
            )
            if matches:
                gain = matches * self._number(config, "deck_enhancement_evidence_weight", 0.35)
                raw += gain
                notes.append(f"enhancement evidence={gain:.3f} from {matches} cards")

        if definition.preferred_seals:
            matches = sum(
                str(getattr(card, "seal", "")) in definition.preferred_seals
                for card in deck
            )
            if matches:
                gain = matches * self._number(config, "deck_seal_evidence_weight", 0.40)
                raw += gain
                notes.append(f"seal evidence={gain:.3f} from {matches} cards")

        if definition.preferred_editions:
            card_matches = sum(
                str(getattr(card, "edition", "")) in definition.preferred_editions
                for card in deck
            )
            joker_matches = sum(
                str(getattr(joker, "edition", "")) in definition.preferred_editions
                for joker in getattr(state, "jokers", ())
            )
            matches = card_matches + joker_matches
            if matches:
                gain = matches * self._number(config, "deck_edition_evidence_weight", 0.25)
                raw += gain
                notes.append(f"edition evidence={gain:.3f} from {matches} components")

        if definition.preferred_ranks and non_stone:
            matches = sum(
                str(getattr(card, "rank", "")) in definition.preferred_ranks
                for card in non_stone
            )
            baseline = total * len(set(definition.preferred_ranks)) / 13.0
            excess = max(0.0, matches - baseline)
            if excess:
                gain = excess * self._number(config, "deck_rank_evidence_weight", 0.30)
                raw += gain
                notes.append(f"preferred rank concentration evidence={gain:.3f}")

        if definition.face_mode and non_stone:
            face_count = sum(
                str(getattr(card, "rank", "")) in {"J", "Q", "K"}
                for card in non_stone
            )
            expected_faces = total * 3.0 / 13.0
            if definition.face_mode.upper() == "FACE":
                delta = max(0.0, face_count - expected_faces)
            else:
                delta = max(0.0, expected_faces - face_count)
            if delta:
                gain = delta * self._number(config, "deck_face_evidence_weight", 0.30)
                raw += gain
                notes.append(f"face-structure evidence={gain:.3f}")

        return raw, tuple(notes)

    def _assess(self, state, definition: StrategyDefinition) -> StrategyAssessment | None:
        config = self._config(state)
        effectiveness = self.effectiveness(state, definition.strategy_id)
        if effectiveness <= 0.0:
            return None

        counts = {GOLD: 0, SILVER: 0, BRONZE: 0, BANNED: 0}
        raw = 0.0
        notes: list[str] = []

        for joker in getattr(state, "jokers", ()):
            relationship = definition.relationship_for(joker, kind="JOKER")
            if relationship == NEUTRAL:
                continue
            counts[relationship] += 1
            gain = self.relationship_score(state, relationship)
            raw += gain
            notes.append(
                f"owned {relationship.lower()} Joker {type(joker).__name__}: {gain:+.3f}"
            )

        # Held/unopened consumables are intentionally absent here. Potential future
        # transformations affect candidate/use value, not current strategy evidence.

        for voucher in getattr(state, "vouchers", ()):
            relationship = definition.relationship_for(voucher, kind="VOUCHER")
            if relationship != NEUTRAL:
                gain = self.relationship_score(state, relationship)
                raw += gain
                notes.append(f"owned {relationship.lower()} voucher: {gain:+.3f}")

        hand_levels = getattr(state, "hand_levels", {}) or {}
        hand_level_weight = self._number(config, "hand_level_evidence_weight", 0.50)
        structural_hand_evidence = False
        for hand in definition.primary_hands:
            extra_levels = max(0, int(hand_levels.get(hand, 1) or 1) - 1)
            if extra_levels:
                structural_hand_evidence = True
            raw += extra_levels * hand_level_weight

        deck_raw, deck_notes = self._deck_evidence(state, definition, config)
        raw += deck_raw
        notes.extend(deck_notes)

        positive_jokers = counts[GOLD] + counts[SILVER] + counts[BRONZE]
        requirements_met = self._has_joker(state, definition.required_jokers)
        if definition.required_jokers and not requirements_met:
            raw = min(raw, float(definition.entry_evidence_cap))
            notes.append("defining Joker requirement not met; positive evidence capped")
        if (
            definition.minimum_positive_jokers > 0
            and positive_jokers < definition.minimum_positive_jokers
            and not structural_hand_evidence
            and deck_raw <= 0.0
        ):
            raw = min(raw, float(definition.entry_evidence_cap))
            notes.append("composite strategy entry requirement not met; positive evidence capped")

        base_score = self.base_strategy_score(state, definition.strategy_id)
        score = base_score + raw * effectiveness
        notes.append(
            f"environment base={base_score:+.3f}; effectiveness={effectiveness:.3f}; raw={raw:.3f}; adjusted={score:.3f}"
        )

        thresholds = (
            (MATURE, self._number(config, "mature_threshold", 16.0)),
            (COMMITTED, self._number(config, "commit_threshold", 9.0)),
            (HIGHLIGHTED, self._number(config, "highlight_threshold", 3.5)),
            (CANDIDATE, self._number(config, "candidate_threshold", 1.5)),
        )
        status = next((name for name, floor in thresholds if score >= floor), AVAILABLE)
        return StrategyAssessment(
            strategy_id=definition.strategy_id,
            name=definition.name,
            score=score,
            effectiveness=effectiveness,
            base_score=base_score,
            status=status,
            gold_owned=counts[GOLD],
            silver_owned=counts[SILVER],
            bronze_owned=counts[BRONZE],
            banned_owned=counts[BANNED],
            rationale=tuple(notes),
        )

    def assess(self, state) -> tuple[StrategyAssessment, ...]:
        assessments = [
            result
            for definition in self.definitions.values()
            if (result := self._assess(state, definition)) is not None
        ]
        return tuple(sorted(assessments, key=lambda a: (-a.score, a.strategy_id)))

    def observe(self, state) -> StrategyResolution:
        config = self._config(state)
        assessments = self.assess(state)
        positive = [a for a in assessments if a.score > 0.0]
        dominant = positive[0] if positive else None

        max_relevant = max(0, int(self._number(config, "max_relevant_strategies", 2.0)))
        relevant_floor = self._number(config, "relevant_strategy_floor", 1.0)
        relevant_ratio = self._number(config, "relevant_strategy_ratio", 0.35)
        relevant: list[StrategyAssessment] = []
        if dominant is not None:
            floor = max(relevant_floor, dominant.score * relevant_ratio)
            relevant = [
                assessment
                for assessment in positive[1:]
                if assessment.score >= floor
            ][:max_relevant]

        ante = max(1, int(getattr(state, "ante", 1) or 1))
        dominant_id = dominant.strategy_id if dominant else None
        relevant_ids = tuple(a.strategy_id for a in relevant)
        active_status = AVAILABLE
        if dominant is not None:
            if dominant.score >= self._number(config, "mature_threshold", 16.0):
                active_status = MATURE
            elif ante >= 6:
                active_status = COMMITTED
            elif dominant.score >= self._number(config, "highlight_threshold", 3.5):
                active_status = HIGHLIGHTED
            else:
                active_status = CANDIDATE

        committed_id = dominant_id if dominant is not None and ante >= 6 else None
        changed = (
            dominant_id != self._last_dominant_strategy_id
            or relevant_ids != self._last_relevant_strategy_ids
        )
        rationale: tuple[str, ...]
        if dominant is None:
            rationale = ("no positive universal strategy evidence; ordinary/meta value leads",)
        else:
            relevant_text = ", ".join(relevant_ids) if relevant_ids else "none"
            rationale = (
                f"dominant strategy={dominant.name} score={dominant.score:.3f}; relevant={relevant_text}; pressure={self.strategy_pressure(state):.3f}",
            )

        self._last_dominant_strategy_id = dominant_id
        self._last_relevant_strategy_ids = relevant_ids
        return StrategyResolution(
            dominant_strategy_id=dominant_id,
            relevant_strategy_ids=relevant_ids,
            active_strategy_id=dominant_id,
            highlighted_strategy_id=dominant_id,
            committed_strategy_id=committed_id,
            active_status=active_status,
            assessments=assessments,
            changed=changed,
            rationale=rationale,
        )

    def _scope_factor(
        self,
        state,
        strategy_id: str,
        rank: int,
        resolution: StrategyResolution,
    ) -> float:
        config = self._config(state)
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante <= 2:
            return 1.0
        if ante <= 5:
            decay = self._number(config, "mid_strategy_rank_decay", 0.15)
            floor = self._number(config, "mid_strategy_rank_floor", 0.25)
            return max(floor, 1.0 - rank * decay)
        if strategy_id == resolution.dominant_strategy_id:
            return 1.0
        if strategy_id in resolution.relevant_strategy_ids:
            index = resolution.relevant_strategy_ids.index(strategy_id)
            return self._number(
                config,
                "first_relevant_strategy_factor" if index == 0 else "second_relevant_strategy_factor",
                0.80 if index == 0 else 0.65,
            )
        return self._number(config, "late_off_shortlist_factor", 0.05)

    def evaluate_item(self, state, item: object, *, kind: str) -> StrategicItemEvaluation:
        kind = str(kind).upper()
        resolution = self.observe(state)
        by_id = {a.strategy_id: a for a in resolution.assessments}
        rank_by_id = {
            assessment.strategy_id: rank
            for rank, assessment in enumerate(resolution.assessments)
        }
        relationships = self._relationships_for(item, kind=kind)
        candidate = str(getattr(item, "name", type(item).__name__))
        if not relationships:
            return StrategicItemEvaluation(
                candidate=candidate,
                kind=kind,
                strategy_id=None,
                strategy_name=None,
                tier=None,
                value=0.0,
                projected_score=0.0,
                active_alignment=False,
                pivot_candidate=False,
                rationale=("item is Neutral to every enabled universal strategy",),
            )

        config = self._config(state)
        pressure = self.strategy_pressure(state)
        alignment_scale = self._number(config, "candidate_alignment_scale", 0.08)
        total_alignment = 0.0
        active_alignment = False
        rationale: list[str] = []
        strongest_strategy_id: str | None = None
        strongest_relationship: str | None = None
        strongest_abs = -1.0
        strongest_projected = 0.0
        fallback_strategy_id: str | None = None
        fallback_relationship: str | None = None
        fallback_projected = 0.0
        fallback_priority = -1
        pivot = False
        dominant = by_id.get(resolution.dominant_strategy_id)

        for strategy_id, relationship in relationships.items():
            assessment = by_id.get(strategy_id)
            definition = self.definitions.get(strategy_id)
            if assessment is None or definition is None:
                continue
            current_positive = max(0.0, assessment.score)
            scope = self._scope_factor(
                state,
                strategy_id,
                rank_by_id.get(strategy_id, 999),
                resolution,
            )
            relation_weight = self.relationship_score(state, relationship)
            contribution = 0.0
            if current_positive > 0.0:
                if relationship == BANNED:
                    contribution = current_positive * relation_weight * scope
                elif relationship in {GOLD, SILVER, BRONZE}:
                    contribution = current_positive * relation_weight * scope
            total_alignment += contribution

            projected = assessment.score + relation_weight * assessment.effectiveness
            shortlisted = strategy_id in resolution.shortlist_strategy_ids
            if shortlisted and relationship in {GOLD, SILVER, BRONZE}:
                active_alignment = True
            if (
                dominant is not None
                and relationship == GOLD
                and strategy_id != dominant.strategy_id
                and projected
                >= dominant.score
                + self._number(
                    config,
                    "early_pivot_margin" if int(getattr(state, "ante", 1) or 1) <= 5 else "late_pivot_margin",
                    1.5 if int(getattr(state, "ante", 1) or 1) <= 5 else 4.0,
                )
            ):
                pivot = True

            positive_priority = _POSITIVE_RELATIONSHIP_PRIORITY[relationship]
            if positive_priority > fallback_priority:
                fallback_priority = positive_priority
                fallback_strategy_id = strategy_id
                fallback_relationship = relationship
                fallback_projected = projected

            if abs(contribution) > strongest_abs or (
                abs(contribution) == strongest_abs
                and _RELATIONSHIP_PRIORITY[relationship]
                > _RELATIONSHIP_PRIORITY.get(strongest_relationship or NEUTRAL, 0)
            ):
                strongest_abs = abs(contribution)
                strongest_strategy_id = strategy_id
                strongest_relationship = relationship
                strongest_projected = projected

            rationale.append(
                f"{candidate}: {relationship} for {definition.name}; current={assessment.score:.3f}; scope={scope:.3f}; raw_alignment={contribution:+.3f}"
            )

        # With no existing strategy evidence every relationship contributes zero.
        # Report the strongest positive relationship in that neutral case so a
        # Gold component remains identifiable as Gold without receiving any
        # strategy purchase bonus. Banned remains primary once it produces an
        # actual negative alignment against a positively evidenced strategy.
        if strongest_abs <= 0.0 and fallback_relationship in {GOLD, SILVER, BRONZE}:
            strongest_strategy_id = fallback_strategy_id
            strongest_relationship = fallback_relationship
            strongest_projected = fallback_projected

        value = total_alignment * alignment_scale * pressure
        strongest_definition = self.definitions.get(strongest_strategy_id or "")
        rationale.append(
            f"strategy alignment total={total_alignment:+.3f}; scale={alignment_scale:.3f}; Ante pressure={pressure:.3f}; purchase adjustment={value:+.3f}"
        )
        return StrategicItemEvaluation(
            candidate=candidate,
            kind=kind,
            strategy_id=strongest_strategy_id,
            strategy_name=(strongest_definition.name if strongest_definition else None),
            tier=strongest_relationship,
            value=value,
            projected_score=strongest_projected,
            active_alignment=active_alignment,
            pivot_candidate=pivot,
            rationale=tuple(rationale),
        )

    def hand_fit(self, state, hand_type: str) -> tuple[float, tuple[str, ...]]:
        resolution = self.observe(state)
        if resolution.dominant_strategy_id is None:
            return 0.0, ("no positive universal strategy evidence",)

        hand_type = str(hand_type).upper()
        pressure = self.strategy_pressure(state)
        shortlist = resolution.shortlist_strategy_ids
        mapped_hand_strategy = False
        for index, strategy_id in enumerate(shortlist):
            definition = self.definitions.get(strategy_id)
            if definition is None or not definition.primary_hands:
                continue
            mapped_hand_strategy = True
            if hand_type in definition.primary_hands:
                strength = 1.0 if index == 0 else 0.65 if index == 1 else 0.45
                return strength * pressure * self.effectiveness(state, strategy_id), (
                    f"{hand_type} reinforces shortlisted strategy {definition.name}",
                )

        if not mapped_hand_strategy:
            return 0.0, ("shortlisted strategies do not prescribe a poker-hand type",)
        return -0.25 * pressure, (
            f"{hand_type} does not reinforce a shortlisted poker-hand strategy",
        )