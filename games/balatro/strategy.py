from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping


GOLD = "GOLD"
SILVER = "SILVER"
BRONZE = "BRONZE"

AVAILABLE = "AVAILABLE"
CANDIDATE = "CANDIDATE"
HIGHLIGHTED = "HIGHLIGHTED"
COMMITTED = "COMMITTED"
MATURE = "MATURE"


_TIER_WEIGHTS = {
    GOLD: 7.5,
    SILVER: 4.0,
    BRONZE: 1.5,
}


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _item_tokens(item: object) -> frozenset[str]:
    values = {
        type(item).__name__,
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "key", ""),
        getattr(item, "center", ""),
    }
    return frozenset(token for value in values if (token := _normalize(value)))


def _normalized_names(values) -> frozenset[str]:
    return frozenset(
        token
        for value in values or ()
        if (token := _normalize(value))
    )


@dataclass(frozen=True)
class StrategyDefinition:
    strategy_id: str
    name: str
    primary_hands: tuple[str, ...] = ()
    gold_jokers: frozenset[str] = frozenset()
    silver_jokers: frozenset[str] = frozenset()
    bronze_jokers: frozenset[str] = frozenset()
    gold_consumables: frozenset[str] = frozenset()
    silver_consumables: frozenset[str] = frozenset()
    bronze_consumables: frozenset[str] = frozenset()
    gold_planets: frozenset[str] = frozenset()
    silver_planets: frozenset[str] = frozenset()
    bronze_planets: frozenset[str] = frozenset()
    gold_vouchers: frozenset[str] = frozenset()
    silver_vouchers: frozenset[str] = frozenset()
    bronze_vouchers: frozenset[str] = frozenset()
    conflicts: frozenset[str] = frozenset()

    @classmethod
    def from_mapping(
        cls,
        strategy_id: str,
        value: Mapping[str, object],
    ) -> "StrategyDefinition":
        def tiered(kind: str, tier: str) -> frozenset[str]:
            block = value.get(kind, {})
            if not isinstance(block, Mapping):
                return frozenset()
            return _normalized_names(block.get(tier.lower(), ()))

        return cls(
            strategy_id=str(strategy_id),
            name=str(value.get("name", strategy_id)),
            primary_hands=tuple(
                str(hand).upper()
                for hand in value.get("primary_hands", ())
            ),
            gold_jokers=tiered("jokers", GOLD),
            silver_jokers=tiered("jokers", SILVER),
            bronze_jokers=tiered("jokers", BRONZE),
            gold_consumables=tiered("consumables", GOLD),
            silver_consumables=tiered("consumables", SILVER),
            bronze_consumables=tiered("consumables", BRONZE),
            gold_planets=tiered("planets", GOLD),
            silver_planets=tiered("planets", SILVER),
            bronze_planets=tiered("planets", BRONZE),
            gold_vouchers=tiered("vouchers", GOLD),
            silver_vouchers=tiered("vouchers", SILVER),
            bronze_vouchers=tiered("vouchers", BRONZE),
            conflicts=_normalized_names(value.get("conflicts", ())),
        )

    def tier_for(self, item: object, *, kind: str) -> str | None:
        tokens = _item_tokens(item)
        kind = str(kind).upper()
        if kind == "JOKER":
            buckets = (
                (GOLD, self.gold_jokers),
                (SILVER, self.silver_jokers),
                (BRONZE, self.bronze_jokers),
            )
        elif kind == "PLANET":
            buckets = (
                (GOLD, self.gold_planets),
                (SILVER, self.silver_planets),
                (BRONZE, self.bronze_planets),
            )
        elif kind == "VOUCHER":
            buckets = (
                (GOLD, self.gold_vouchers),
                (SILVER, self.silver_vouchers),
                (BRONZE, self.bronze_vouchers),
            )
        else:
            buckets = (
                (GOLD, self.gold_consumables),
                (SILVER, self.silver_consumables),
                (BRONZE, self.bronze_consumables),
            )

        for tier, names in buckets:
            if tokens & names:
                return tier
        return None

    def conflicts_with(self, item: object) -> bool:
        return bool(_item_tokens(item) & self.conflicts)


@dataclass(frozen=True)
class StrategyAssessment:
    strategy_id: str
    name: str
    score: float
    status: str
    gold_owned: int
    silver_owned: int
    bronze_owned: int
    hand_investment: float
    hand_history: float
    conflict_count: int
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyResolution:
    highlighted_strategy_id: str | None
    committed_strategy_id: str | None
    active_strategy_id: str | None
    active_status: str
    assessments: tuple[StrategyAssessment, ...]
    changed: bool = False
    rationale: tuple[str, ...] = ()

    def assessment(self, strategy_id: str | None) -> StrategyAssessment | None:
        if strategy_id is None:
            return None
        return next(
            (
                assessment
                for assessment in self.assessments
                if assessment.strategy_id == strategy_id
            ),
            None,
        )


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


class BalatroStrategyTracker:
    """Run-scoped cartridge strategy resolver.

    The tracker consumes only current public state and explicit strategy definitions
    supplied by the active playbook cartridge. It never predicts hidden shop/pack
    contents. A Gold/Silver pickup can highlight an archetype immediately, while
    commitment and later pivots depend on accumulated owned pieces and hand
    investment. Antes 1-4 remain deliberately easier to pivot than later antes.
    """

    def __init__(
        self,
        catalog_provider: Callable[[object], Mapping[str, object]],
    ) -> None:
        self.catalog_provider = catalog_provider
        self.highlighted_strategy_id: str | None = None
        self.committed_strategy_id: str | None = None
        self._last_active_strategy_id: str | None = None

    def reset(self) -> None:
        self.highlighted_strategy_id = None
        self.committed_strategy_id = None
        self._last_active_strategy_id = None

    def _catalog(self, state) -> tuple[dict[str, StrategyDefinition], Mapping[str, object]]:
        raw = self.catalog_provider(state) or {}
        if not isinstance(raw, Mapping):
            raise TypeError("playbook strategy_catalog must be a mapping")
        raw_definitions = raw.get("definitions", {})
        if not isinstance(raw_definitions, Mapping):
            raise TypeError("playbook strategy_catalog definitions must be a mapping")
        definitions = {
            str(strategy_id): StrategyDefinition.from_mapping(
                str(strategy_id),
                definition,
            )
            for strategy_id, definition in raw_definitions.items()
            if isinstance(definition, Mapping)
        }
        return definitions, raw

    def _threshold(self, config: Mapping[str, object], key: str, default: float) -> float:
        try:
            return float(config.get(key, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _owned_items(state, kind: str) -> tuple[object, ...]:
        kind = kind.upper()
        if kind == "JOKER":
            return tuple(getattr(state, "jokers", ()))
        if kind in {"CONSUMABLE", "PLANET"}:
            return tuple(getattr(state, "consumables", ()))
        if kind == "VOUCHER":
            return tuple(getattr(state, "vouchers", ()))
        return ()

    def _assess_definition(
        self,
        state,
        definition: StrategyDefinition,
        config: Mapping[str, object],
    ) -> StrategyAssessment:
        gold_weight = self._threshold(config, "gold_weight", _TIER_WEIGHTS[GOLD])
        silver_weight = self._threshold(config, "silver_weight", _TIER_WEIGHTS[SILVER])
        bronze_weight = self._threshold(config, "bronze_weight", _TIER_WEIGHTS[BRONZE])
        held_consumable_fraction = self._threshold(
            config,
            "held_consumable_fraction",
            0.35,
        )
        hand_level_weight = self._threshold(config, "hand_level_weight", 1.25)
        hand_history_weight = self._threshold(config, "hand_history_weight", 0.45)
        conflict_penalty = self._threshold(config, "conflict_penalty", 5.0)

        tier_counts = {GOLD: 0, SILVER: 0, BRONZE: 0}
        score = 0.0
        notes: list[str] = []

        for joker in self._owned_items(state, "JOKER"):
            tier = definition.tier_for(joker, kind="JOKER")
            if tier is not None:
                tier_counts[tier] += 1
                amount = {
                    GOLD: gold_weight,
                    SILVER: silver_weight,
                    BRONZE: bronze_weight,
                }[tier]
                score += amount
                notes.append(
                    f"owned {tier.lower()} Joker {getattr(joker, 'name', type(joker).__name__)} +{amount:.2f}"
                )

        for consumable in self._owned_items(state, "CONSUMABLE"):
            category = str(getattr(consumable, "category", "")).upper()
            kind = "PLANET" if category == "PLANET" else "CONSUMABLE"
            tier = definition.tier_for(consumable, kind=kind)
            if tier is not None:
                amount = {
                    GOLD: gold_weight,
                    SILVER: silver_weight,
                    BRONZE: bronze_weight,
                }[tier] * held_consumable_fraction
                score += amount
                notes.append(
                    f"held {tier.lower()} {kind.lower()} {getattr(consumable, 'name', type(consumable).__name__)} +{amount:.2f}"
                )

        for voucher in self._owned_items(state, "VOUCHER"):
            tier = definition.tier_for(voucher, kind="VOUCHER")
            if tier is not None:
                amount = {
                    GOLD: gold_weight,
                    SILVER: silver_weight,
                    BRONZE: bronze_weight,
                }[tier]
                score += amount
                notes.append(
                    f"owned {tier.lower()} Voucher {getattr(voucher, 'name', type(voucher).__name__)} +{amount:.2f}"
                )

        hand_levels = getattr(state, "hand_levels", {}) or {}
        play_counts = getattr(state, "hand_play_counts", {}) or {}
        hand_investment = 0.0
        hand_history = 0.0
        for hand_type in definition.primary_hands:
            level = int(hand_levels.get(hand_type, 1) or 1)
            played = int(play_counts.get(hand_type, 0) or 0)
            hand_investment += max(0, level - 1) * hand_level_weight
            hand_history += min(6, max(0, played)) * hand_history_weight
        score += hand_investment + hand_history
        if hand_investment:
            notes.append(f"primary-hand level investment +{hand_investment:.2f}")
        if hand_history:
            notes.append(f"primary-hand play history +{hand_history:.2f}")

        conflicts = sum(
            1
            for joker in self._owned_items(state, "JOKER")
            if definition.conflicts_with(joker)
        )
        if conflicts:
            score -= conflicts * conflict_penalty
            notes.append(
                f"strategy conflicts={conflicts} -{conflicts * conflict_penalty:.2f}"
            )

        candidate_threshold = self._threshold(config, "candidate_threshold", 1.5)
        highlight_threshold = self._threshold(config, "highlight_threshold", 3.5)
        commit_threshold = self._threshold(config, "commit_threshold", 9.0)
        mature_threshold = self._threshold(config, "mature_threshold", 16.0)
        if score >= mature_threshold:
            status = MATURE
        elif score >= commit_threshold:
            status = COMMITTED
        elif score >= highlight_threshold:
            status = HIGHLIGHTED
        elif score >= candidate_threshold:
            status = CANDIDATE
        else:
            status = AVAILABLE

        return StrategyAssessment(
            strategy_id=definition.strategy_id,
            name=definition.name,
            score=score,
            status=status,
            gold_owned=tier_counts[GOLD],
            silver_owned=tier_counts[SILVER],
            bronze_owned=tier_counts[BRONZE],
            hand_investment=hand_investment,
            hand_history=hand_history,
            conflict_count=conflicts,
            rationale=tuple(notes),
        )

    def assess(self, state) -> tuple[StrategyAssessment, ...]:
        definitions, config = self._catalog(state)
        return tuple(
            sorted(
                (
                    self._assess_definition(state, definition, config)
                    for definition in definitions.values()
                ),
                key=lambda assessment: (-assessment.score, assessment.strategy_id),
            )
        )

    def observe(self, state) -> StrategyResolution:
        definitions, config = self._catalog(state)
        assessments = tuple(
            sorted(
                (
                    self._assess_definition(state, definition, config)
                    for definition in definitions.values()
                ),
                key=lambda assessment: (-assessment.score, assessment.strategy_id),
            )
        )
        best = assessments[0] if assessments else None
        previous_highlight = self.highlighted_strategy_id
        previous_commit = self.committed_strategy_id
        ante = int(getattr(state, "ante", 1) or 1)

        highlight_threshold = self._threshold(config, "highlight_threshold", 3.5)
        commit_threshold = self._threshold(config, "commit_threshold", 9.0)
        mature_threshold = self._threshold(config, "mature_threshold", 16.0)
        early_pivot_margin = self._threshold(config, "early_pivot_margin", 1.5)
        late_pivot_margin = self._threshold(config, "late_pivot_margin", 4.0)

        by_id = {assessment.strategy_id: assessment for assessment in assessments}
        current = by_id.get(self.highlighted_strategy_id)

        if best is not None and best.score >= highlight_threshold:
            if current is None:
                self.highlighted_strategy_id = best.strategy_id
            elif best.strategy_id != current.strategy_id:
                pivot_margin = early_pivot_margin if ante <= 4 else late_pivot_margin
                if best.score >= current.score + pivot_margin:
                    self.highlighted_strategy_id = best.strategy_id

        highlighted = by_id.get(self.highlighted_strategy_id)
        if highlighted is not None and highlighted.score >= commit_threshold:
            if self.committed_strategy_id is None:
                self.committed_strategy_id = highlighted.strategy_id
            elif self.committed_strategy_id != highlighted.strategy_id:
                committed = by_id.get(self.committed_strategy_id)
                incumbent_score = committed.score if committed is not None else 0.0
                pivot_margin = early_pivot_margin if ante <= 4 else late_pivot_margin
                if highlighted.score >= incumbent_score + pivot_margin:
                    self.committed_strategy_id = highlighted.strategy_id

        active_id = self.committed_strategy_id or self.highlighted_strategy_id
        active = by_id.get(active_id)
        if active is None:
            active_status = AVAILABLE
        elif active.score >= mature_threshold:
            active_status = MATURE
        elif self.committed_strategy_id == active_id:
            active_status = COMMITTED
        else:
            active_status = HIGHLIGHTED

        changed = (
            previous_highlight != self.highlighted_strategy_id
            or previous_commit != self.committed_strategy_id
            or self._last_active_strategy_id != active_id
        )
        notes: list[str] = []
        if changed:
            notes.append(
                f"strategy active {self._last_active_strategy_id or 'NONE'} -> {active_id or 'NONE'}"
            )
        if active is not None:
            notes.append(
                f"strategy {active.name} score={active.score:.3f} status={active_status}"
            )
        self._last_active_strategy_id = active_id

        return StrategyResolution(
            highlighted_strategy_id=self.highlighted_strategy_id,
            committed_strategy_id=self.committed_strategy_id,
            active_strategy_id=active_id,
            active_status=active_status,
            assessments=assessments,
            changed=changed,
            rationale=tuple(notes),
        )

    def evaluate_item(
        self,
        state,
        item: object,
        *,
        kind: str,
    ) -> StrategicItemEvaluation:
        definitions, config = self._catalog(state)
        resolution = self.observe(state)
        by_id = {assessment.strategy_id: assessment for assessment in resolution.assessments}
        active_id = resolution.active_strategy_id
        active = by_id.get(active_id)

        gold_value = self._threshold(config, "gold_item_value", 8.0)
        silver_value = self._threshold(config, "silver_item_value", 4.5)
        bronze_value = self._threshold(config, "bronze_item_value", 1.5)
        active_multiplier = self._threshold(config, "active_alignment_multiplier", 1.35)
        off_strategy_penalty = self._threshold(config, "off_strategy_penalty", 2.0)
        early_pivot_margin = self._threshold(config, "early_pivot_margin", 1.5)
        late_pivot_margin = self._threshold(config, "late_pivot_margin", 4.0)
        ante = int(getattr(state, "ante", 1) or 1)
        pivot_margin = early_pivot_margin if ante <= 4 else late_pivot_margin

        base_by_tier = {
            GOLD: gold_value,
            SILVER: silver_value,
            BRONZE: bronze_value,
        }
        candidates: list[StrategicItemEvaluation] = []
        candidate_label = str(getattr(item, "name", type(item).__name__))
        kind = str(kind).upper()

        for definition in definitions.values():
            tier = definition.tier_for(item, kind=kind)
            if tier is None:
                continue
            assessment = by_id.get(definition.strategy_id)
            current_score = assessment.score if assessment is not None else 0.0
            projected = current_score + _TIER_WEIGHTS[tier]
            aligned = active_id == definition.strategy_id
            value = base_by_tier[tier]
            pivot_candidate = False

            if aligned:
                value *= active_multiplier
            elif active is not None:
                if tier == GOLD and projected >= active.score + pivot_margin:
                    pivot_candidate = True
                elif tier != GOLD:
                    value -= off_strategy_penalty

            rationale = [
                f"strategy item {candidate_label} tier={tier} for {definition.name}",
                f"strategy score {current_score:.3f} -> projected {projected:.3f}",
            ]
            if aligned:
                rationale.append(
                    f"aligned with active strategy; x{active_multiplier:.2f} priority"
                )
            elif pivot_candidate:
                rationale.append("Gold item is strong enough to justify a strategy pivot candidate")
            elif active is not None and tier != GOLD:
                rationale.append(
                    f"off-strategy {tier.lower()} piece penalized by {off_strategy_penalty:.2f}"
                )

            candidates.append(
                StrategicItemEvaluation(
                    candidate=candidate_label,
                    kind=kind,
                    strategy_id=definition.strategy_id,
                    strategy_name=definition.name,
                    tier=tier,
                    value=value,
                    projected_score=projected,
                    active_alignment=aligned,
                    pivot_candidate=pivot_candidate,
                    rationale=tuple(rationale),
                )
            )

        if not candidates:
            return StrategicItemEvaluation(
                candidate=candidate_label,
                kind=kind,
                strategy_id=None,
                strategy_name=None,
                tier=None,
                value=0.0,
                projected_score=0.0,
                active_alignment=False,
                pivot_candidate=False,
                rationale=(
                    f"{candidate_label} is not a Gold/Silver/Bronze component of any cartridge strategy",
                ),
            )

        return max(
            candidates,
            key=lambda evaluation: (
                evaluation.value,
                evaluation.projected_score,
                evaluation.tier == GOLD,
                evaluation.tier == SILVER,
                evaluation.strategy_id or "",
            ),
        )

    def hand_fit(self, state, hand_type: str) -> tuple[float, tuple[str, ...]]:
        definitions, _ = self._catalog(state)
        resolution = self.observe(state)
        active_id = resolution.active_strategy_id
        if active_id is None:
            return 0.0, ("no highlighted cartridge strategy; strategic hand fit=0",)
        definition = definitions.get(active_id)
        if definition is None:
            return 0.0, ("active cartridge strategy definition unavailable",)

        hand_type = str(hand_type).upper()
        if hand_type in definition.primary_hands:
            value = 1.0 if resolution.active_status in {COMMITTED, MATURE} else 0.75
            return value, (
                f"strategic hand {hand_type} matches active {definition.name} ({resolution.active_status})",
            )
        return -0.35, (
            f"hand {hand_type} is off-strategy for active {definition.name}",
        )
