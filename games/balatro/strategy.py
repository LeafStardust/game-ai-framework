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

_TIER_SCORE = {GOLD: 7.5, SILVER: 4.0, BRONZE: 1.5}
_TIER_VALUE = {GOLD: 8.0, SILVER: 4.5, BRONZE: 1.5}


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
    """Universal strategy knowledge; never owned by a deck/stake cartridge."""

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

    def tier_for(self, item: object, *, kind: str) -> str | None:
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
        item_tokens = _tokens(item)
        for tier, names in buckets:
            if item_tokens & names:
                return tier
        return None

    def conflicts_with(self, item: object) -> bool:
        return bool(_tokens(item) & self.conflicts)


@dataclass(frozen=True)
class StrategyAssessment:
    strategy_id: str
    name: str
    score: float
    effectiveness: float
    status: str
    gold_owned: int
    silver_owned: int
    bronze_owned: int
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyResolution:
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
    """Resolve run intent from universal strategies plus environment modifiers.

    ``modifier_provider`` is the only cartridge hook. It may disable strategies or
    scale their effectiveness, but it never changes what the strategy actually is.
    """

    def __init__(
        self,
        definitions: Mapping[str, StrategyDefinition],
        *,
        modifier_provider: Callable[[object], Mapping[str, object]] | None = None,
    ) -> None:
        self.definitions = dict(definitions)
        self.modifier_provider = modifier_provider or (lambda state: {})
        self.highlighted_strategy_id: str | None = None
        self.committed_strategy_id: str | None = None
        self._last_active_strategy_id: str | None = None

    def reset(self) -> None:
        self.highlighted_strategy_id = None
        self.committed_strategy_id = None
        self._last_active_strategy_id = None

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

    def effectiveness(self, state, strategy_id: str) -> float:
        config = self._config(state)
        modifier = self._modifier(config, strategy_id)
        if modifier.get("enabled", True) is False:
            return 0.0
        try:
            return max(0.0, float(modifier.get("effectiveness", 1.0)))
        except (TypeError, ValueError):
            return 1.0

    def _assess(self, state, definition: StrategyDefinition) -> StrategyAssessment | None:
        config = self._config(state)
        effectiveness = self.effectiveness(state, definition.strategy_id)
        if effectiveness <= 0.0:
            return None

        counts = {GOLD: 0, SILVER: 0, BRONZE: 0}
        raw = 0.0
        notes: list[str] = []
        held_fraction = self._number(config, "held_consumable_fraction", 0.35)

        for joker in getattr(state, "jokers", ()):
            tier = definition.tier_for(joker, kind="JOKER")
            if tier:
                counts[tier] += 1
                raw += _TIER_SCORE[tier]
                notes.append(f"owned {tier.lower()} Joker {type(joker).__name__}")

        for consumable in getattr(state, "consumables", ()):
            kind = (
                "PLANET"
                if str(getattr(consumable, "category", "")).upper() == "PLANET"
                else "CONSUMABLE"
            )
            tier = definition.tier_for(consumable, kind=kind)
            if tier:
                raw += _TIER_SCORE[tier] * held_fraction
                notes.append(
                    f"held {tier.lower()} {kind.lower()} {getattr(consumable, 'name', type(consumable).__name__)}"
                )

        for voucher in getattr(state, "vouchers", ()):
            tier = definition.tier_for(voucher, kind="VOUCHER")
            if tier:
                raw += _TIER_SCORE[tier]

        hand_level_weight = self._number(config, "hand_level_weight", 1.25)
        hand_history_weight = self._number(config, "hand_history_weight", 0.45)
        hand_levels = getattr(state, "hand_levels", {}) or {}
        hand_counts = getattr(state, "hand_play_counts", {}) or {}
        for hand in definition.primary_hands:
            raw += max(0, int(hand_levels.get(hand, 1) or 1) - 1) * hand_level_weight
            raw += min(6, max(0, int(hand_counts.get(hand, 0) or 0))) * hand_history_weight

        conflicts = sum(
            1 for joker in getattr(state, "jokers", ()) if definition.conflicts_with(joker)
        )
        raw -= conflicts * self._number(config, "conflict_penalty", 5.0)
        modifier = self._modifier(config, definition.strategy_id)
        try:
            bonus = float(modifier.get("score_bonus", 0.0))
        except (TypeError, ValueError):
            bonus = 0.0
        score = raw * effectiveness + bonus
        notes.append(
            f"environment effectiveness={effectiveness:.3f}; raw={raw:.3f}; adjusted={score:.3f}"
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
            status=status,
            gold_owned=counts[GOLD],
            silver_owned=counts[SILVER],
            bronze_owned=counts[BRONZE],
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
        by_id = {a.strategy_id: a for a in assessments}
        best = assessments[0] if assessments else None
        old_highlight = self.highlighted_strategy_id
        old_commit = self.committed_strategy_id

        if self.highlighted_strategy_id not in by_id:
            self.highlighted_strategy_id = None
        if self.committed_strategy_id not in by_id:
            self.committed_strategy_id = None

        highlight_floor = self._number(config, "highlight_threshold", 3.5)
        commit_floor = self._number(config, "commit_threshold", 9.0)
        pivot_margin = self._number(
            config,
            "early_pivot_margin" if int(getattr(state, "ante", 1) or 1) <= 4 else "late_pivot_margin",
            1.5 if int(getattr(state, "ante", 1) or 1) <= 4 else 4.0,
        )

        current = by_id.get(self.highlighted_strategy_id)
        if best and best.score >= highlight_floor:
            if current is None or (
                best.strategy_id != current.strategy_id
                and best.score >= current.score + pivot_margin
            ):
                self.highlighted_strategy_id = best.strategy_id

        highlighted = by_id.get(self.highlighted_strategy_id)
        committed = by_id.get(self.committed_strategy_id)
        if highlighted and highlighted.score >= commit_floor:
            if committed is None or (
                highlighted.strategy_id != committed.strategy_id
                and highlighted.score >= committed.score + pivot_margin
            ):
                self.committed_strategy_id = highlighted.strategy_id

        active_id = self.committed_strategy_id or self.highlighted_strategy_id
        active = by_id.get(active_id)
        active_status = (
            MATURE
            if active and active.score >= self._number(config, "mature_threshold", 16.0)
            else COMMITTED
            if active and self.committed_strategy_id == active_id
            else HIGHLIGHTED
            if active
            else AVAILABLE
        )
        changed = (
            old_highlight != self.highlighted_strategy_id
            or old_commit != self.committed_strategy_id
            or self._last_active_strategy_id != active_id
        )
        notes = () if not active else (
            f"active strategy={active.name} score={active.score:.3f} effectiveness={active.effectiveness:.3f} status={active_status}",
        )
        self._last_active_strategy_id = active_id
        return StrategyResolution(
            active_strategy_id=active_id,
            highlighted_strategy_id=self.highlighted_strategy_id,
            committed_strategy_id=self.committed_strategy_id,
            active_status=active_status,
            assessments=assessments,
            changed=changed,
            rationale=notes,
        )

    def evaluate_item(self, state, item: object, *, kind: str) -> StrategicItemEvaluation:
        resolution = self.observe(state)
        by_id = {a.strategy_id: a for a in resolution.assessments}
        active = by_id.get(resolution.active_strategy_id)
        config = self._config(state)
        candidate = str(getattr(item, "name", type(item).__name__))
        options: list[StrategicItemEvaluation] = []

        for definition in self.definitions.values():
            effectiveness = self.effectiveness(state, definition.strategy_id)
            if effectiveness <= 0.0:
                continue
            tier = definition.tier_for(item, kind=kind)
            if tier is None:
                continue
            assessment = by_id.get(definition.strategy_id)
            current = assessment.score if assessment else 0.0
            projected = current + _TIER_SCORE[tier] * effectiveness
            aligned = resolution.active_strategy_id == definition.strategy_id
            value = _TIER_VALUE[tier] * effectiveness
            if aligned:
                value *= self._number(config, "active_alignment_multiplier", 1.35)
            pivot_margin = self._number(
                config,
                "early_pivot_margin" if int(getattr(state, "ante", 1) or 1) <= 4 else "late_pivot_margin",
                1.5 if int(getattr(state, "ante", 1) or 1) <= 4 else 4.0,
            )
            pivot = bool(active and tier == GOLD and projected >= active.score + pivot_margin)
            if active and not aligned and tier != GOLD:
                value -= self._number(config, "off_strategy_penalty", 2.0)
            options.append(
                StrategicItemEvaluation(
                    candidate=candidate,
                    kind=str(kind).upper(),
                    strategy_id=definition.strategy_id,
                    strategy_name=definition.name,
                    tier=tier,
                    value=value,
                    projected_score=projected,
                    active_alignment=aligned,
                    pivot_candidate=pivot,
                    rationale=(
                        f"{candidate} is {tier} for universal strategy {definition.name}",
                        f"environment effectiveness={effectiveness:.3f}",
                        f"projected strategy score={projected:.3f}",
                    ),
                )
            )

        if not options:
            return StrategicItemEvaluation(
                candidate=candidate,
                kind=str(kind).upper(),
                strategy_id=None,
                strategy_name=None,
                tier=None,
                value=0.0,
                projected_score=0.0,
                active_alignment=False,
                pivot_candidate=False,
                rationale=("item is not part of any enabled universal strategy",),
            )
        return max(
            options,
            key=lambda option: (
                option.value,
                option.projected_score,
                option.tier == GOLD,
                option.tier == SILVER,
            ),
        )

    def hand_fit(self, state, hand_type: str) -> tuple[float, tuple[str, ...]]:
        resolution = self.observe(state)
        active_id = resolution.active_strategy_id
        if active_id is None:
            return 0.0, ("no active universal strategy",)
        definition = self.definitions.get(active_id)
        if definition is None:
            return 0.0, ("active universal strategy definition unavailable",)
        effectiveness = self.effectiveness(state, active_id)
        hand_type = str(hand_type).upper()
        if hand_type in definition.primary_hands:
            commitment = 1.0 if resolution.active_status in {COMMITTED, MATURE} else 0.75
            return commitment * effectiveness, (
                f"{hand_type} is the active strategic hand for {definition.name}",
            )
        return -0.35 * effectiveness, (
            f"{hand_type} is off-strategy for active {definition.name}",
        )
