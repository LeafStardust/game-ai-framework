from __future__ import annotations

from collections import Counter
from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.live.hand_action_policy import PACE_RECOVERY
from games.balatro.live.hand_playstyle import BuildAwareLiveHandActionPolicy
from games.balatro.strategy import BRONZE, GOLD, SILVER, BalatroStrategyTracker
from games.balatro.strategy_compat import NeutralLegacyPlaystyleIntentTracker


_RANK_VALUE = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
}

_JOKER_HAND_TIER_WEIGHT = {
    GOLD: 1.00,
    SILVER: 0.65,
    BRONZE: 0.30,
}


class StrategyAwareLiveHandActionPolicy(BuildAwareLiveHandActionPolicy):
    """D1 survival hierarchy with universal-playbook pursuit beneath it.

    The inherited clear-probability/exactness/expected-hands dimensions remain
    ahead of strategy. Its retained-card preservation mechanics are also kept, but
    the legacy playstyle-intent signal is neutralized so the universal playbooks are
    the only strategic direction used by this policy.

    Critically, the base D1 pace floor is authoritative. If a legal current play
    can score at least remaining blind score / hands remaining, strategy shaping
    may choose among qualifying plays but may not replace that play with a discard.
    Discards are therefore the default setup tool only while no current hand meets
    the required pace.
    """

    VAGABOND_PLAY_OPPORTUNITY_VALUE = 35.0

    def __init__(self, *args, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        kwargs["intent_tracker"] = NeutralLegacyPlaystyleIntentTracker()
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker
        self._hand_evaluator = HandEvaluator()

    def decide(self, state, plans, **kwargs):
        decision = super().decide(state, plans, **kwargs)
        vagabond_active = self._vagabond_generation_active(state)

        # Final-hand survival is absolute. If no current play meets pace, spending
        # the final remaining hand loses immediately. Any legal discard is therefore
        # better than an under-pace PLAY regardless of Banner/no-discard strategy,
        # retained-card utility, or other strategic shaping.
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
            discards = [
                plan for plan in plans if plan.action.name == DISCARD_CARDS
            ]
            if discards:
                selected = max(
                    discards,
                    key=lambda plan: (
                        float(self.evaluator.evaluate(state, plan.action)),
                        self._within_type_key(plan),
                    ),
                )
                selected_value = float(self.evaluator.evaluate(state, selected.action))
                decision = replace(
                    decision,
                    mode=PACE_RECOVERY,
                    action=selected.action,
                    selected_plan=selected,
                    selected_immediate_score=None,
                    selected_pace_ratio=None,
                    selected_fallback_value=selected_value,
                    confidence=max(float(decision.confidence), 0.95),
                    rationale=(
                        "final hand cannot currently clear the blind",
                        "legal discards remain, so playing an under-pace final hand would lose immediately",
                        "survival overrides Banner/no-discard and all other strategy preferences",
                        "use a discard and re-observe for a stronger final hand",
                    ),
                )

        # Do not override a base PACE_PLAY decision with a setup discard. The base
        # policy already establishes that some current hand meets the mandatory
        # remaining-score / hands-remaining pace floor. Strategy/Joker intent is a
        # tie-breaker beneath survival, not permission to postpone a qualifying play.
        fit, rationale = self._strategy_fit(state, decision.action)
        return replace(
            decision,
            rationale=(
                *decision.rationale,
                *(
                    (
                        "Vagabond active at <=$4 with consumable space; safe equivalent lines may value additional scored hands for Tarot generation",
                    )
                    if vagabond_active
                    else ()
                ),
                "pace-qualified PLAY is authoritative; strategy shaping cannot replace it with DISCARD",
                "D1 legacy playstyle strategy influence=0.000",
                f"D1 universal-strategy fit={fit:+.3f}",
                *rationale,
            ),
        )

    def _within_type_key(self, plan):
        base = super()._within_type_key(plan)
        if self._ranking_state is None:
            return base
        fit, _ = self._strategy_fit(self._ranking_state, plan.action)
        vagabond = self._vagabond_generation_active(self._ranking_state)
        hand_use = (
            -float(plan.value.expected_hands_remaining)
            if vagabond and plan.action.name == PLAY_CARDS
            else float(plan.value.expected_hands_remaining)
        )
        # BuildAware D1 places held Steel/Blue-Seal preservation at base[2].
        # Universal/owned-Joker hand fit stays below survival and retained-card value.
        return (base[0], base[1], base[2], fit, hand_use, *base[4:])

    def _safe_equivalent_clear_key(self, plan):
        base = super()._safe_equivalent_clear_key(plan)
        if self._ranking_state is None:
            return base
        fit, _ = self._strategy_fit(self._ranking_state, plan.action)
        if self._vagabond_generation_active(self._ranking_state):
            # Only inside the already-safe equivalence set: prefer consuming another
            # real hand so Vagabond produces another Tarot instead of speed-clearing.
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
        if not any(
            type(joker).__name__ == "VagabondJoker"
            for joker in getattr(state, "jokers", ()) or ()
        ):
            return False
        consumable_slots = int(getattr(state, "consumable_slots", 2) or 2)
        return len(getattr(state, "consumables", ()) or ()) < consumable_slots

    def _owned_joker_hand_weights(self, state) -> dict[str, float]:
        """Return poker-hand incentives implied directly by currently owned Jokers.

        Shop/strategy scoring already knows which Jokers are Gold/Silver/Bronze for
        each poker-hand strategy. D1 must use the same information before the route
        is formally committed; otherwise a hand-trigger Joker can be owned while the
        discard policy ignores the hand that makes that Joker useful.
        """
        weights: dict[str, float] = {}
        relationships_for = getattr(self.strategy_tracker, "_relationships_for", None)
        if not callable(relationships_for):
            return weights

        for joker in getattr(state, "jokers", ()) or ():
            relationships = relationships_for(joker, kind="JOKER")
            for strategy_id, tier in relationships.items():
                tier_weight = _JOKER_HAND_TIER_WEIGHT.get(tier)
                if tier_weight is None:
                    continue
                effectiveness = self.strategy_tracker.effectiveness(state, strategy_id)
                if effectiveness <= 0.0:
                    continue
                for hand_type in self.strategy_tracker.primary_hands_for(strategy_id):
                    hand = str(hand_type).upper()
                    weights[hand] = weights.get(hand, 0.0) + tier_weight * effectiveness
        return weights

    def _strategy_fit(self, state, action) -> tuple[float, tuple[str, ...]]:
        joker_hand_weights = self._owned_joker_hand_weights(state)

        if action.name == PLAY_CARDS:
            hand_type = self._hand_evaluator.evaluate(list(action.cards)).value
            strategy_value, strategy_rationale = self.strategy_tracker.hand_fit(
                state,
                hand_type,
            )
            joker_value = joker_hand_weights.get(str(hand_type).upper(), 0.0)
            return strategy_value + joker_value, (
                *strategy_rationale,
                f"D1 owned-Joker hand incentive {hand_type}={joker_value:+.3f}",
            )

        if action.name != DISCARD_CARDS:
            return 0.0, ("D1 action has no strategic-hand structure signal",)

        removed = {id(card) for card in action.cards}
        kept = [card for card in getattr(state, "hand", ()) if id(card) not in removed]
        intents: list[tuple[str, float, str]] = []

        resolution = self.strategy_tracker.observe(state)
        strategy_id = resolution.active_strategy_id
        if strategy_id is not None:
            definition = self.strategy_tracker.definitions.get(strategy_id)
            effectiveness = self.strategy_tracker.effectiveness(state, strategy_id)
            for hand_type in self.strategy_tracker.primary_hands_for(strategy_id):
                intents.append(
                    (
                        str(hand_type).upper(),
                        effectiveness,
                        definition.name if definition is not None else str(strategy_id),
                    )
                )

        for hand_type, weight in joker_hand_weights.items():
            intents.append((hand_type, weight, "owned Jokers"))

        if not intents:
            return 0.0, (
                "no active strategy or owned hand-specific Joker for discard shaping",
            )

        scored = [
            (
                self._structure_fit(kept, hand_type) * weight,
                self._structure_fit(kept, hand_type),
                hand_type,
                weight,
                source,
            )
            for hand_type, weight, source in intents
            if weight > 0.0
        ]
        if not scored:
            return 0.0, ("no positive hand intent for discard shaping",)

        value, structure, hand_type, weight, source = max(
            scored,
            key=lambda item: (item[0], item[1], item[3], item[2]),
        )
        return value, (
            f"D1 discard preserves {hand_type} structure={structure:.3f}",
            f"D1 hand intent source={source} weight={weight:.3f}",
            "owned Joker hand requirements participate before formal strategy commitment",
        )

    @classmethod
    def _structure_fit(cls, cards, hand_type: str) -> float:
        hand_type = str(hand_type).upper()
        ranks = Counter(str(getattr(card, "rank", "")) for card in cards)
        suits = Counter(str(getattr(card, "suit", "")) for card in cards)
        rank_counts = sorted(ranks.values(), reverse=True)
        maximum_rank = rank_counts[0] if rank_counts else 0
        maximum_suit = max(suits.values(), default=0)

        if hand_type == "HIGH_CARD":
            return 0.25 if cards else 0.0
        if hand_type == "PAIR":
            return min(1.0, maximum_rank / 2.0)
        if hand_type == "TWO_PAIR":
            pair_slots = sum(1 for count in rank_counts if count >= 2)
            return min(1.0, pair_slots / 2.0)
        if hand_type == "THREE_OF_A_KIND":
            return min(1.0, maximum_rank / 3.0)
        if hand_type == "FOUR_OF_A_KIND":
            return min(1.0, maximum_rank / 4.0)
        if hand_type == "FIVE_OF_A_KIND":
            return min(1.0, maximum_rank / 5.0)
        if hand_type == "FLUSH":
            return min(1.0, maximum_suit / 5.0)
        if hand_type == "STRAIGHT":
            return cls._straight_fit(cards)
        if hand_type == "FULL_HOUSE":
            top = rank_counts[0] if rank_counts else 0
            second = rank_counts[1] if len(rank_counts) > 1 else 0
            return 0.6 * min(1.0, top / 3.0) + 0.4 * min(1.0, second / 2.0)
        if hand_type == "STRAIGHT_FLUSH":
            return max(
                (
                    cls._straight_fit(
                        [card for card in cards if str(getattr(card, "suit", "")) == suit]
                    )
                    for suit in suits
                ),
                default=0.0,
            )
        if hand_type == "FLUSH_HOUSE":
            full_house = cls._structure_fit(cards, "FULL_HOUSE")
            flush = cls._structure_fit(cards, "FLUSH")
            return full_house * flush
        if hand_type == "FLUSH_FIVE":
            five = cls._structure_fit(cards, "FIVE_OF_A_KIND")
            flush = cls._structure_fit(cards, "FLUSH")
            return five * flush
        return 0.0

    @staticmethod
    def _straight_fit(cards) -> float:
        values = {
            _RANK_VALUE.get(str(getattr(card, "rank", "")))
            for card in cards
        }
        values.discard(None)
        if 14 in values:
            values.add(1)
        best = 0
        for low in range(1, 11):
            best = max(best, sum(1 for value in range(low, low + 5) if value in values))
        return min(1.0, best / 5.0)
