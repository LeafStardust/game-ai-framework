from __future__ import annotations

from collections import Counter
from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondRank, BondRealization
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import card_matches_suit, hand_rules_for_state
from games.balatro.live.hand_action_policy import PACE_RECOVERY
from games.balatro.live.hand_build_policy import BuildAwareLiveHandActionPolicy


_RANK_VALUE = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
    "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}

_REALIZATION_WEIGHT = {
    BondRealization.DORMANT: 0.00,
    BondRealization.PARTIAL: 0.25,
    BondRealization.ACTIVE: 0.75,
    BondRealization.MATURE: 1.25,
}

# Strategy fit is only a within-safe-choice preference. These values must never be
# large enough to replace pace/survival legality; the parent D1 hierarchy decides
# that before this signal is consulted.
_PINNED_HELD_CARD_VALUE = 1.25
_PINNED_RED_SEAL_HELD_BONUS = 0.40


class StrategyAwareLiveHandActionPolicy(BuildAwareLiveHandActionPolicy):
    """D1 survival hierarchy with canonical Bond/composition pursuit beneath it."""

    VAGABOND_PLAY_OPPORTUNITY_VALUE = 35.0

    def __init__(self, *args, strategy_tracker=None, **kwargs) -> None:
        del strategy_tracker
        super().__init__(*args, **kwargs)
        self._hand_evaluator = HandEvaluator()

    def decide(self, state, plans, **kwargs):
        decision = super().decide(state, plans, **kwargs)
        vagabond_active = self._vagabond_generation_active(state)
        if (
            decision.action.name == PLAY_CARDS
            and int(getattr(state, "hands_remaining", 0) or 0) <= 1
            and int(getattr(state, "discards_remaining", 0) or 0) > 0
            and (
                decision.selected_pace_ratio is None
                or float(decision.selected_pace_ratio) + self.EPSILON
                < float(self.thresholds.pace_ratio_floor)
            )
        ):
            discards = [plan for plan in plans if plan.action.name == DISCARD_CARDS]
            if discards:
                selected = max(
                    discards,
                    key=lambda plan: (
                        *self._within_type_key(plan),
                        float(self.evaluator.evaluate(state, plan.action)),
                    ),
                )
                decision = replace(
                    decision,
                    mode=PACE_RECOVERY,
                    action=selected.action,
                    selected_plan=selected,
                    selected_immediate_score=None,
                    selected_pace_ratio=None,
                    selected_fallback_value=float(self.evaluator.evaluate(state, selected.action)),
                    confidence=max(float(decision.confidence), 0.95),
                    rationale=(
                        "final hand cannot currently clear the blind",
                        "legal discards remain, so playing an under-pace final hand would lose immediately",
                        "survival overrides all Bond/composition preferences",
                        "use the strongest full-blind D1 discard line and re-observe for a stronger final hand",
                    ),
                )
        fit, rationale = self._strategy_fit(state, decision.action)
        return replace(
            decision,
            rationale=(
                *decision.rationale,
                *(("Vagabond active at <=$4 with consumable space; safe equivalent lines may value additional scored hands for Tarot generation",) if vagabond_active else ()),
                "pace-qualified PLAY is authoritative; Bond shaping cannot replace it with DISCARD",
                f"D1 Bond/composition fit={fit:+.3f}",
                *rationale,
            ),
        )

    def _within_type_key(self, plan):
        base = super()._within_type_key(plan)
        if self._ranking_state is None:
            return base
        fit, _ = self._strategy_fit(self._ranking_state, plan.action)
        hand_use = (
            -float(plan.value.expected_hands_remaining)
            if self._vagabond_generation_active(self._ranking_state) and plan.action.name == PLAY_CARDS
            else float(plan.value.expected_hands_remaining)
        )
        return (base[0], base[1], base[2], fit, hand_use, *base[3:])

    def _safe_equivalent_clear_key(self, plan):
        base = super()._safe_equivalent_clear_key(plan)
        if self._ranking_state is None:
            return base
        fit, _ = self._strategy_fit(self._ranking_state, plan.action)
        if self._vagabond_generation_active(self._ranking_state):
            return (base[0], -base[1], base[2], fit, *base[3:])
        return (base[0], base[1], base[2], fit, *base[3:])

    def _pace_play_key(self, plan, pace_ratio: float):
        base = super()._pace_play_key(plan, pace_ratio)
        if self._ranking_state is None:
            return base
        fit, _ = self._strategy_fit(self._ranking_state, plan.action)
        return (base[0], base[1], base[2], fit, *base[3:])

    @staticmethod
    def _vagabond_generation_active(state) -> bool:
        if int(getattr(state, "money", 0) or 0) > 4:
            return False
        if not any(type(joker).__name__ == "VagabondJoker" for joker in getattr(state, "jokers", ()) or ()):
            return False
        consumable_slots = int(getattr(state, "consumable_slots", 2) or 2)
        return len(getattr(state, "consumables", ()) or ()) < consumable_slots

    @staticmethod
    def _bond_weight(development) -> float:
        if not development.unlocked or development.rank < BondRank.R1:
            return 0.0
        rank = float(int(development.rank))
        realization = _REALIZATION_WEIGHT[development.realization]
        progress = 0.0
        if development.next_rank_threshold:
            progress = min(0.75, max(0.0, float(development.contribution) / float(development.next_rank_threshold)))
        return rank + realization + progress

    def _composition(self, state):
        try:
            return evaluate_bond_composition(state)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return (), None

    def _hand_bond_intents(self, state) -> list[tuple[str, float, str]]:
        developments, composition = self._composition(state)
        if composition is None:
            return []
        selected = set(composition.bond_ids)
        intents: list[tuple[str, float, str]] = []
        for development in developments:
            target = str(development.target or "").upper()
            if not target or development.bond_id not in selected:
                continue
            weight = self._bond_weight(development)
            if weight > 0.0:
                intents.append((target, weight, development.bond_id))
        return intents

    @staticmethod
    def _pinned_candidate(composition):
        if composition is None:
            return None
        pinned_id = getattr(composition, "pinned_strategy_id", None)
        if not pinned_id:
            return None
        return next(
            (
                candidate
                for candidate in getattr(composition, "strategy_candidates", ()) or ()
                if candidate.strategy_id == pinned_id and candidate.pinned
            ),
            None,
        )

    @classmethod
    def _pinned_held_card_value(cls, candidate, card) -> tuple[float, tuple[str, ...]]:
        """Return strategic held value of one card for the pinned engine.

        Held-oriented candidate Bonds supply the semantic context. Rank/enhancement
        membership is derived from the candidate itself rather than a Joker-pair
        lookup, so any future held-King/Queen/Steel package inherits the behavior.
        """
        if candidate is None:
            return 0.0, ()
        bonds = set(candidate.bond_ids)
        prescriptions = tuple(str(item) for item in candidate.prescriptions)
        held_oriented = bool(bonds & {"held_cards", "held_retrigger"}) or any(
            "held" in item for item in prescriptions
        )
        if not held_oriented:
            return 0.0, ()

        rank = str(getattr(card, "rank", "") or "").upper()
        enhancement = str(getattr(card, "enhancement", "") or "").lower()
        seal = str(getattr(card, "seal", "") or "").lower()
        value = 0.0
        reasons: list[str] = []

        rank_bonds = {"K": "kings", "Q": "queens", "A": "aces", "J": "jacks"}
        rank_bond = rank_bonds.get(rank)
        if rank_bond and rank_bond in bonds:
            value += _PINNED_HELD_CARD_VALUE
            reasons.append(f"pinned {candidate.strategy_id} preserves held {rank}")
        if enhancement == "steel" and "steel" in bonds:
            value += _PINNED_HELD_CARD_VALUE
            reasons.append(f"pinned {candidate.strategy_id} preserves held Steel")
        if seal == "red" and value > 0.0 and "held_retrigger" in bonds:
            value += _PINNED_RED_SEAL_HELD_BONUS
            reasons.append("Red Seal amplifies pinned held engine")
        return value, tuple(reasons)

    def _pinned_card_preservation(self, state, action) -> tuple[float, tuple[str, ...]]:
        _, composition = self._composition(state)
        candidate = self._pinned_candidate(composition)
        if candidate is None or action.name not in {PLAY_CARDS, DISCARD_CARDS}:
            return 0.0, ()

        sacrificed = tuple(action.cards)
        total = 0.0
        notes: list[str] = []
        for card in sacrificed:
            value, reasons = self._pinned_held_card_value(candidate, card)
            total += value
            notes.extend(reasons)
        if total <= 0.0:
            return 0.0, (f"pinned strategy {candidate.strategy_id} sacrifices no held-engine card",)
        # Playing/discarding an engine card both remove it from hand. Negative fit is
        # only a tie-break among actions already accepted by the parent survival path.
        return -total, tuple(dict.fromkeys(notes))

    def _strategy_fit(self, state, action) -> tuple[float, tuple[str, ...]]:
        intents = self._hand_bond_intents(state)
        preservation, preservation_notes = self._pinned_card_preservation(state, action)
        rules = hand_rules_for_state(state)

        if action.name == PLAY_CARDS:
            hand_type = self._hand_evaluator.evaluate(
                list(action.cards),
                rules=rules,
            ).value
            matches = [(weight, source) for target, weight, source in intents if target == str(hand_type).upper()]
            if not matches:
                return preservation, (
                    f"no developed Bond targets {hand_type}",
                    f"pinned held-card preservation={preservation:+.3f}",
                    *preservation_notes,
                )
            weight, source = max(matches)
            return weight + preservation, (
                f"D1 {source} Bond targets {hand_type} weight={weight:.3f}",
                f"pinned held-card preservation={preservation:+.3f}",
                *preservation_notes,
            )

        if action.name != DISCARD_CARDS:
            return preservation, ("D1 action has no Bond hand-structure signal", *preservation_notes)

        removed = {id(card) for card in action.cards}
        kept = [card for card in getattr(state, "hand", ()) if id(card) not in removed]
        if not intents:
            return preservation, (
                "no developed hand-target Bond for discard shaping",
                f"pinned held-card preservation={preservation:+.3f}",
                *preservation_notes,
            )
        scored = [
            (
                self._structure_fit(kept, hand_type, rules=rules) * weight,
                self._structure_fit(kept, hand_type, rules=rules),
                hand_type,
                weight,
                source,
            )
            for hand_type, weight, source in intents
        ]
        value, structure, hand_type, weight, source = max(scored, key=lambda item: (item[0], item[1], item[3], item[2]))
        return value + preservation, (
            f"D1 discard preserves {hand_type} structure={structure:.3f}",
            f"D1 Bond intent source={source} weight={weight:.3f}",
            f"pinned held-card preservation={preservation:+.3f}",
            *preservation_notes,
        )

    @classmethod
    def _structure_fit(cls, cards, hand_type: str, *, rules: dict | None = None) -> float:
        rules = dict(rules or {})
        hand_type = str(hand_type).upper()
        regular = [
            card
            for card in cards
            if str(getattr(card, "enhancement", "") or "") != "Stone"
        ]
        ranks = Counter(str(getattr(card, "rank", "")) for card in regular)
        rank_counts = sorted(ranks.values(), reverse=True)
        maximum_rank = rank_counts[0] if rank_counts else 0
        flush_required = max(1, int(rules.get("flush_size", 5) or 5))
        maximum_suit = max(
            (
                sum(1 for card in regular if card_matches_suit(card, suit, rules))
                for suit in ("Hearts", "Diamonds", "Clubs", "Spades")
            ),
            default=0,
        )
        if hand_type == "HIGH_CARD": return 0.25 if regular else 0.0
        if hand_type == "PAIR": return min(1.0, maximum_rank / 2.0)
        if hand_type == "TWO_PAIR": return min(1.0, sum(1 for count in rank_counts if count >= 2) / 2.0)
        if hand_type == "THREE_OF_A_KIND": return min(1.0, maximum_rank / 3.0)
        if hand_type == "FOUR_OF_A_KIND": return min(1.0, maximum_rank / 4.0)
        if hand_type == "FIVE_OF_A_KIND": return min(1.0, maximum_rank / 5.0)
        if hand_type == "FLUSH": return min(1.0, maximum_suit / float(flush_required))
        if hand_type == "STRAIGHT": return cls._straight_fit(regular, rules=rules)
        if hand_type == "FULL_HOUSE":
            top = rank_counts[0] if rank_counts else 0
            second = rank_counts[1] if len(rank_counts) > 1 else 0
            return 0.6 * min(1.0, top / 3.0) + 0.4 * min(1.0, second / 2.0)
        if hand_type == "STRAIGHT_FLUSH":
            return max(
                (
                    cls._straight_fit(
                        [card for card in regular if card_matches_suit(card, suit, rules)],
                        rules=rules,
                    )
                    for suit in ("Hearts", "Diamonds", "Clubs", "Spades")
                ),
                default=0.0,
            )
        if hand_type == "FLUSH_HOUSE": return cls._structure_fit(regular, "FULL_HOUSE", rules=rules) * cls._structure_fit(regular, "FLUSH", rules=rules)
        if hand_type == "FLUSH_FIVE": return cls._structure_fit(regular, "FIVE_OF_A_KIND", rules=rules) * cls._structure_fit(regular, "FLUSH", rules=rules)
        return 0.0

    @staticmethod
    def _straight_fit(cards, *, rules: dict | None = None) -> float:
        rules = dict(rules or {})
        required = max(1, int(rules.get("straight_size", 5) or 5))
        max_step = 2 if bool(rules.get("shortcut")) else 1
        raw_values = {
            _RANK_VALUE.get(str(getattr(card, "rank", "")))
            for card in cards
        }
        raw_values.discard(None)
        if not raw_values:
            return 0.0

        value_sets = [set(raw_values)]
        if 14 in raw_values:
            ace_low = set(raw_values)
            ace_low.remove(14)
            ace_low.add(1)
            value_sets.append(ace_low)

        best = 1
        for values in value_sets:
            ordered = sorted(values)
            for start in range(len(ordered)):
                length = 1
                previous = ordered[start]
                for current in ordered[start + 1:]:
                    gap = current - previous
                    if 1 <= gap <= max_step:
                        length += 1
                        previous = current
                    elif gap > max_step:
                        break
                best = max(best, length)
        return min(1.0, best / float(required))
