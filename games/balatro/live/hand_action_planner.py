from __future__ import annotations

from itertools import combinations

from games.balatro.actions import BalatroAction, PLAY_CARDS, USE_CONSUMABLE
from games.balatro.blinds.blind import BlindType
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.blind_clear_planner import LiveBlindPlanValue, _ActionEstimate
from games.balatro.live.boss_blind_integration import boss_play_action_is_legal
from games.balatro.live.consumable_timing import LiveConsumableTimingPolicy
from games.balatro.live.hand_action_planner_core import (
    D1LiveBlindClearPlanner as _CoreD1LiveBlindClearPlanner,
)


class D1LiveBlindClearPlanner(_CoreD1LiveBlindClearPlanner):
    """D1 planner with deterministic consumables and passive Joker hand rules.

    The core Play/Discard search stays intact. This integration layer additionally
    keeps passive public hand rules (for example Four Fingers, Shortcut and Splash)
    consistent across root ranking and bounded recursive child generation, then may
    add one deterministic held-consumable clear candidate at the authoritative root.

    Real execution still performs only the selected first semantic action and then
    re-observes/replans. Boss-blind consumable integration remains deliberately
    excluded until the generalized boss-mechanics item is completed.
    """

    def __init__(
        self,
        *args,
        consumable_timing_policy: LiveConsumableTimingPolicy | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.consumable_timing_policy = (
            consumable_timing_policy
            or LiveConsumableTimingPolicy(
                hand_evaluator=self.evaluator,
                defer_blind_clear_to_d1=False,
            )
        )
        self._integrated_consumable_estimates: dict[int, _ActionEstimate] = {}
        self._active_hand_rules: dict = {}

    def reset_search_stats(self) -> None:
        super().reset_search_stats()
        self._integrated_consumable_estimates.clear()

    def _candidate_actions(
        self,
        state,
        *,
        allow_discards: bool,
        play_width: int | None = None,
        discard_width: int | None = None,
    ):
        previous_rules = self._active_hand_rules
        self._active_hand_rules = hand_rules_for_state(state)
        try:
            root_beam = self.nodes_evaluated == 0
            actions = super()._candidate_actions(
                state,
                allow_discards=allow_discards,
                play_width=play_width,
                discard_width=discard_width,
            )
            if not root_beam:
                return actions

            blind = getattr(state, "blind", None)
            if getattr(blind, "type", None) == BlindType.BOSS:
                return actions

            for recommendation in (
                self.consumable_timing_policy.blind_clear_recommendations(state)
            ):
                # The Sun retains its separately validated multi-target escape path.
                # This integration covers the remaining deterministic B6/D5/D6 uses.
                if str(getattr(recommendation.consumable, "name", "")) == "The Sun":
                    continue

                action = recommendation.to_action()
                if action is None:
                    continue
                estimate = self._estimate_from_recommendation(
                    state,
                    action,
                    recommendation,
                )
                if estimate is None:
                    continue

                self._integrated_consumable_estimates[id(action)] = estimate
                return [*actions, action]

            return actions
        finally:
            self._active_hand_rules = previous_rules

    def _child_play_candidates(self, state, play_limit: int):
        """Augment the bounded core child set with passive-rule made hands."""
        base = super()._child_play_candidates(state, play_limit)
        rules = dict(self._active_hand_rules or hand_rules_for_state(state))
        if not rules:
            return base

        hand = list(getattr(state, "hand", ()))
        if not hand:
            return base

        max_cards = min(self.action_generator.MAX_SELECTED_CARDS, len(hand))
        candidates = {self._action_identity(action): action for action in base}

        def add(cards) -> None:
            cards = list(cards)[:max_cards]
            if not cards:
                return
            action = BalatroAction(PLAY_CARDS, cards=cards)
            if not boss_play_action_is_legal(state, action):
                return
            candidates.setdefault(self._action_identity(action), action)

        straight = self._best_straight_cards(hand)
        add(straight)

        flush_cards = self.evaluator.hand_evaluator._flush_cards(hand, rules)
        flush_required = max(1, int(rules.get("flush_size", 5) or 5))
        flush_subset = self._best_flush_subset(
            flush_cards,
            flush_required,
            prefer=straight,
        )
        add(flush_subset)

        # A longer legal flush can still be useful as a cycling variant.
        if len(flush_cards) > flush_required:
            add(
                sorted(
                    flush_cards,
                    key=self._card_visible_value,
                    reverse=True,
                )[:max_cards]
            )

        # Four Fingers permits the straight and flush components of a Straight
        # Flush to come from different four-card subsets of one <=5-card play.
        if straight and flush_subset:
            selected_ids = {id(card) for card in straight}
            selected_ids.update(id(card) for card in flush_subset)
            union = [card for card in hand if id(card) in selected_ids]
            if len(union) <= max_cards:
                add(union)

        # Also retain an ordinary same-suit/same-colour straight-flush candidate.
        if flush_cards:
            add(self._best_straight_cards(flush_cards))

        projection_limit = min(
            self._MAX_CHILD_PROJECTED_PLAYS,
            max(3, max(1, play_limit) * 3),
        )
        return sorted(
            candidates.values(),
            key=self._direct_child_play_priority,
            reverse=True,
        )[:projection_limit]

    def _direct_child_play_priority(self, action):
        hand = self._search_hand(action.cards)
        scoring = self.evaluator.scorer.scoring_cards(
            hand,
            action.cards,
            rules=self._active_hand_rules,
        )
        visible_chips = sum(self._card_visible_value(card) for card in scoring)
        return (
            self._HAND_STRENGTH.get(hand.value, -1),
            visible_chips,
            len(scoring),
            -len(action.cards),
        )

    def _best_straight_cards(self, cards):
        """Return one best visible straight under the active passive rules."""
        cards = list(cards or [])
        rules = self._active_hand_rules
        required = max(1, int(rules.get("straight_size", 5) or 5))
        if len(cards) < required:
            return []

        max_step = 2 if rules.get("shortcut") else 1
        best_by_rank: dict[str, object] = {}
        for card in cards:
            rank = str(getattr(card, "rank", ""))
            if rank not in self.evaluator.hand_evaluator.RANK_ORDER:
                continue
            current = best_by_rank.get(rank)
            if (
                current is None
                or self._card_visible_value(card) > self._card_visible_value(current)
            ):
                best_by_rank[rank] = card

        if len(best_by_rank) < required:
            return []

        best_combo = None
        best_key = None
        rank_order = self.evaluator.hand_evaluator.RANK_ORDER
        for ranks in combinations(best_by_rank, required):
            values = sorted(rank_order[rank] for rank in ranks)
            value_orders = [values]
            if "A" in ranks:
                value_orders.append(
                    sorted(1 if value == rank_order["A"] else value for value in values)
                )

            if not any(
                all(
                    1 <= current - previous <= max_step
                    for previous, current in zip(ordered, ordered[1:])
                )
                for ordered in value_orders
            ):
                continue

            combo = [best_by_rank[rank] for rank in ranks]
            key = (
                sum(self._card_visible_value(card) for card in combo),
                sum(rank_order[str(card.rank)] for card in combo),
            )
            if best_key is None or key > best_key:
                best_key = key
                best_combo = combo

        if not best_combo:
            return []
        selected_ids = {id(card) for card in best_combo}
        return [card for card in cards if id(card) in selected_ids]

    def _diverse_play_beam(self, state, plays, limit: int):
        if limit <= 0 or not plays:
            return []

        ranked = sorted(
            plays,
            key=lambda action: self._play_priority(state, action),
            reverse=True,
        )
        top = ranked[0]
        chosen = [top]
        chosen_keys = {self._action_identity(top)}
        if len(chosen) >= limit:
            return chosen

        top_hand = self._search_hand(top.cards)
        top_core = self._scoring_core(top_hand, top.cards)
        max_cards = min(
            self.action_generator.MAX_SELECTED_CARDS,
            len(getattr(state, "hand", [])),
        )

        for amount in range(len(top.cards) + 1, max_cards + 1):
            variants = []
            for action in plays:
                if len(action.cards) != amount:
                    continue
                hand = self._search_hand(action.cards)
                if hand != top_hand:
                    continue
                if self._scoring_core(hand, action.cards) != top_core:
                    continue
                variants.append(action)

            if not variants:
                continue
            best = max(
                variants,
                key=lambda action: self._cycling_variant_priority(state, action),
            )
            key = self._action_identity(best)
            if key in chosen_keys:
                continue
            chosen.append(best)
            chosen_keys.add(key)
            if len(chosen) >= limit:
                return chosen

        for action in ranked:
            key = self._action_identity(action)
            if key in chosen_keys:
                continue
            chosen.append(action)
            chosen_keys.add(key)
            if len(chosen) >= limit:
                break
        return chosen

    def _cycling_variant_priority(self, state, action):
        kept = self._kept_cards(state.hand, action.cards)
        retained_structure = self.evaluator._retained_structure_value(kept)
        hand = self._search_hand(action.cards)
        scoring_ids = set(self._scoring_core(hand, action.cards))
        cycled = [card for card in action.cards if id(card) not in scoring_ids]
        cycle_cost = sum(self._cycle_cost(card) for card in cycled)
        return (
            retained_structure,
            -cycle_cost,
            self._play_priority(state, action),
        )

    def _scoring_core(self, hand, cards) -> tuple[int, ...]:
        scoring = self.evaluator.scorer.scoring_cards(
            hand,
            cards,
            rules=self._active_hand_rules,
        )
        return tuple(sorted(id(card) for card in scoring))

    def _search_hand(self, cards):
        return self.evaluator.hand_evaluator.evaluate(
            list(cards or []),
            rules=self._active_hand_rules,
        )

    def _best_flush_subset(self, cards, required: int, *, prefer=()):
        cards = list(cards or [])
        if len(cards) < required:
            return []

        preferred_ids = {id(card) for card in prefer}
        ranked = sorted(
            cards,
            key=lambda card: (
                id(card) in preferred_ids,
                self._card_visible_value(card),
            ),
            reverse=True,
        )
        selected_ids = {id(card) for card in ranked[:required]}
        return [card for card in cards if id(card) in selected_ids]

    def _estimate_action(self, state, action: BalatroAction, depth: int):
        if action.name != USE_CONSUMABLE:
            return super()._estimate_action(state, action, depth)

        estimate = self._integrated_consumable_estimates.get(id(action))
        if estimate is None:
            estimate = self._matching_integrated_estimate(state, action)
        if estimate is not None:
            self._consume_node()
            return estimate

        return super()._estimate_action(state, action, depth)

    def _matching_integrated_estimate(
        self,
        state,
        action: BalatroAction,
    ) -> _ActionEstimate | None:
        """Rebuild a cached estimate for confirmation/root-action evaluation."""
        for recommendation in self.consumable_timing_policy.blind_clear_recommendations(
            state
        ):
            if str(getattr(recommendation.consumable, "name", "")) == "The Sun":
                continue
            candidate = recommendation.to_action()
            if candidate is None:
                continue
            if candidate.target is not action.target:
                continue
            if self._selected_identity(candidate) != self._selected_identity(action):
                continue
            return self._estimate_from_recommendation(state, action, recommendation)
        return None

    @staticmethod
    def _selected_identity(action: BalatroAction) -> tuple[int, ...]:
        return tuple(sorted(id(card) for card in action.cards))

    @staticmethod
    def _estimate_from_recommendation(
        state,
        action: BalatroAction,
        recommendation,
    ) -> _ActionEstimate | None:
        after = recommendation.after_projection
        before = recommendation.before_projection
        if (
            before is None
            or after is None
            or not before.joker_projection_complete
            or not after.joker_projection_complete
            or before.clears_blind
            or not after.clears_blind
        ):
            return None

        return _ActionEstimate(
            action=action,
            value=LiveBlindPlanValue(
                clear_probability=1.0,
                expected_progress=1.0,
                expected_score=float(after.expected_projected_total),
                expected_hands_remaining=float(
                    max(0, int(getattr(state, "hands_remaining", 0)) - 1)
                ),
                expected_discards_remaining=float(
                    getattr(state, "discards_remaining", 0)
                ),
            ),
            exact=True,
        )
