from __future__ import annotations

from collections import Counter
from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.live.hand_action_policy import PACE_PLAY, PACE_RECOVERY
from games.balatro.live.hand_playstyle import BuildAwareLiveHandActionPolicy
from games.balatro.strategy import BalatroStrategyTracker
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


class StrategyAwareLiveHandActionPolicy(BuildAwareLiveHandActionPolicy):
    """D1 survival hierarchy with universal-playbook pursuit beneath it.

    The inherited clear-probability/exactness/expected-hands dimensions remain
    ahead of strategy. Its retained-card preservation mechanics are also kept, but
    the legacy playstyle-intent signal is neutralized so the universal playbooks are
    the only strategic direction used by this policy.
    """

    def __init__(self, *args, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        kwargs["intent_tracker"] = NeutralLegacyPlaystyleIntentTracker()
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker
        self._hand_evaluator = HandEvaluator()

    def decide(self, state, plans, **kwargs):
        decision = super().decide(state, plans, **kwargs)

        # Base D1 returns PACE_PLAY immediately when any current hand reaches
        # remaining_blind_score / hands_remaining. That threshold is a fallback,
        # not a command to throw away available setup equity. Before accepting it,
        # compare legal discards on the same pace-aware cross-action evaluator used
        # by PACE_RECOVERY. A materially better discard is allowed to improve the
        # next hand first; low-discard-reserve protection remains intact.
        if decision.mode == PACE_PLAY:
            discards = [plan for plan in plans if plan.action.name == DISCARD_CARDS]
            if discards:
                play_value = float(self.evaluator.evaluate(state, decision.action))
                scored_discards = []
                for plan in discards:
                    value = float(self.evaluator.evaluate(state, plan.action))
                    if (
                        int(getattr(state, "discards_remaining", 0))
                        <= self.thresholds.low_discard_reserve
                    ):
                        value -= self.thresholds.low_discard_fallback_penalty
                    if (
                        int(getattr(state, "hands_remaining", 0))
                        <= self.thresholds.low_hand_reserve
                    ):
                        value += self.thresholds.low_hand_discard_fallback_bonus
                    strategy_fit, _ = self._strategy_fit(state, plan.action)
                    scored_discards.append((value, strategy_fit, plan))

                discard_value, _, discard_plan = max(
                    scored_discards,
                    key=lambda item: (
                        item[0],
                        item[1],
                        self._within_type_key(item[2]),
                    ),
                )
                consensus = bool(kwargs.get("setup_discard_consensus", False))
                if discard_value > play_value:
                    fit, fit_rationale = self._strategy_fit(state, discard_plan.action)
                    decision = replace(
                        decision,
                        mode=PACE_RECOVERY,
                        action=discard_plan.action,
                        selected_plan=discard_plan,
                        selected_immediate_score=None,
                        selected_pace_ratio=None,
                        selected_fallback_value=discard_value,
                        setup_discard_consensus=consensus,
                        rationale=(
                            "adaptive search found no credible blind-clear path",
                            "a current play reaches required pace, but pace is only the fallback floor",
                            "pace-aware setup discard has higher recovery value than immediate pace play",
                            *(
                                ("deep adaptive searches also agree on the setup discard",)
                                if consensus
                                else ()
                            ),
                            f"D1 setup-discard strategy fit={fit:+.3f}",
                            *fit_rationale,
                        ),
                    )

        fit, rationale = self._strategy_fit(state, decision.action)
        return replace(
            decision,
            rationale=(
                *decision.rationale,
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
        # BuildAware D1 places held Steel/Blue-Seal preservation at base[2].
        # Universal strategy fit must not jump ahead of that public card value.
        return (base[0], base[1], base[2], fit, *base[3:])

    def _safe_equivalent_clear_key(self, plan):
        base = super()._safe_equivalent_clear_key(plan)
        if self._ranking_state is None:
            return base
        fit, _ = self._strategy_fit(self._ranking_state, plan.action)
        return (base[0], base[1], base[2], fit, *base[3:])

    def _pace_play_key(self, plan, pace_ratio: float):
        base = super()._pace_play_key(plan, pace_ratio)
        if self._ranking_state is None:
            return base
        fit, _ = self._strategy_fit(self._ranking_state, plan.action)
        return (base[0], base[1], base[2], fit, *base[3:])

    def _strategy_fit(self, state, action) -> tuple[float, tuple[str, ...]]:
        if action.name == PLAY_CARDS:
            hand_type = self._hand_evaluator.evaluate(list(action.cards)).value
            return self.strategy_tracker.hand_fit(state, hand_type)

        if action.name != DISCARD_CARDS:
            return 0.0, ("D1 action has no strategic-hand structure signal",)

        resolution = self.strategy_tracker.observe(state)
        strategy_id = resolution.active_strategy_id
        if strategy_id is None:
            return 0.0, ("no active universal strategy for discard shaping",)
        definition = self.strategy_tracker.definitions.get(strategy_id)
        primary_hands = self.strategy_tracker.primary_hands_for(strategy_id)
        if definition is None or not primary_hands:
            return 0.0, ("active strategy has no primary hand",)

        removed = {id(card) for card in action.cards}
        kept = [card for card in getattr(state, "hand", ()) if id(card) not in removed]
        structure = max(
            self._structure_fit(kept, hand_type)
            for hand_type in primary_hands
        )
        effectiveness = self.strategy_tracker.effectiveness(state, strategy_id)
        value = structure * effectiveness
        return value, (
            f"D1 discard retains {definition.name} structure={structure:.3f}",
            f"D1 strategy environment effectiveness={effectiveness:.3f}",
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
