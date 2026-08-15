from __future__ import annotations

from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.boss_blind_integration import (
    BossAwareLiveHandDecisionEvaluator,
    boss_play_action_is_legal,
)


class D1LiveBlindClearPlanner(LiveBlindClearPlanner):
    """D1-specific expectimax beam that preserves redraw-size diversity.

    The generic live planner ranks candidates by immediate scoring/retained
    structure and then truncates. That is useful as a broad default, but D1 needs
    to compare strategically distinct ways of spending a hand or discard.

    For Play, keep the best immediate play and reserve larger variants that use
    the same scoring core while cycling extra non-scoring cards. For Discard,
    reserve the best candidate for each redraw size before filling remaining beam
    slots by the generic priority. Beam widths therefore stay bounded while D1
    sees materially different actions instead of near-duplicates.

    A guaranteed immediate blind clear is terminal for D1. When one is currently
    visible, discard branches are suppressed entirely and only guaranteed clearing
    plays are returned. This prevents expectimax from spending an unnecessary
    discard to chase a higher terminal score after the blind can already be won.

    Root Play/Discard candidates remain exhaustive so currently visible decisions
    keep full coverage. Recursive hypothetical states never enumerate every card
    subset. They construct a small deterministic public-state-only candidate set
    directly from the visible hand, then run expensive Joker/score projection only
    on those representatives. Hidden draw order is never consulted.

    Validated boss-blind mechanics are supplied through the shared boss integration
    layer. Root and recursive Play candidates therefore obey the same legality
    rules, while score projection can dispatch to a boss-specific evaluator without
    changing the D1 search algorithm itself.
    """

    _HAND_STRENGTH = {
        "HIGH_CARD": 0,
        "PAIR": 1,
        "TWO_PAIR": 2,
        "THREE_OF_A_KIND": 3,
        "STRAIGHT": 4,
        "FLUSH": 5,
        "FULL_HOUSE": 6,
        "FOUR_OF_A_KIND": 7,
        "STRAIGHT_FLUSH": 8,
    }
    _MAX_CHILD_PROJECTED_PLAYS = 6

    def __init__(self, *args, **kwargs):
        if kwargs.get("evaluator") is None:
            kwargs["evaluator"] = BossAwareLiveHandDecisionEvaluator()
        super().__init__(*args, **kwargs)
        self._play_projection_cache: dict[tuple[int, ...], object] = {}
        self.play_projections_evaluated = 0

    def reset_search_stats(self) -> None:
        super().reset_search_stats()
        self._play_projection_cache.clear()
        self.play_projections_evaluated = 0

    def _play_projection(self, state, action):
        key = self._action_identity(action)
        cached = self._play_projection_cache.get(key)
        if cached is not None:
            return cached

        projection = self.evaluator.project_play(state, action)
        self._play_projection_cache[key] = projection
        self.play_projections_evaluated += 1
        return projection

    def _play_priority(self, state, action):
        projection = self._play_projection(state, action)
        return (
            projection.clear_probability,
            projection.expected_hand_score,
            projection.hand_score,
            -len(action.cards),
        )

    def _candidate_actions(
        self,
        state,
        *,
        allow_discards: bool,
        play_width: int | None = None,
        discard_width: int | None = None,
    ):
        play_limit = self.play_width if play_width is None else int(play_width)
        discard_limit = (
            self.discard_width if discard_width is None else int(discard_width)
        )

        previous_cache = self._play_projection_cache
        self._play_projection_cache = {}
        try:
            # rank_plans()/plan() construct the authoritative root beam before the
            # first search node is consumed. Recursive child beams have already
            # consumed at least one node and therefore use bounded direct candidate
            # construction instead of enumerating every subset.
            root_beam = self.nodes_evaluated == 0
            if root_beam:
                plays = [
                    action
                    for action in self.action_generator.generate_play_actions(state)
                    if boss_play_action_is_legal(state, action)
                ]
            else:
                plays = self._child_play_candidates(state, play_limit)

            guaranteed_clears = [
                action
                for action in plays
                if self._play_projection(state, action).clears_blind
            ]
            if guaranteed_clears:
                return sorted(
                    guaranteed_clears,
                    key=lambda action: self._play_priority(state, action),
                    reverse=True,
                )[: max(0, play_limit)]

            ranked_plays = self._diverse_play_beam(
                state,
                plays,
                play_limit,
            )

            if (
                not allow_discards
                or discard_limit <= 0
                or int(getattr(state, "discards_remaining", 0)) <= 0
            ):
                return ranked_plays

            if root_beam:
                discards = self.action_generator.generate_discard_actions(state)
            else:
                discards = self._child_discard_candidates(state)
            ranked_discards = self._diverse_discard_beam(
                state,
                discards,
                discard_limit,
            )
            return ranked_plays + ranked_discards
        finally:
            self._play_projection_cache = previous_cache

    def _child_play_candidates(self, state, play_limit: int):
        """Construct a bounded strategic child Play set without subset scans."""
        hand = list(getattr(state, "hand", ()))
        if not hand:
            return []

        max_cards = min(self.action_generator.MAX_SELECTED_CARDS, len(hand))
        candidates: dict[tuple[int, ...], BalatroAction] = {}

        def add(cards) -> None:
            cards = list(cards)[:max_cards]
            if not cards:
                return
            action = BalatroAction(PLAY_CARDS, cards=cards)
            if not boss_play_action_is_legal(state, action):
                return
            candidates.setdefault(self._action_identity(action), action)

        # Cheap high-chip prefixes guarantee basic coverage for every selectable
        # card count without constructing combinations.
        high_cards = sorted(hand, key=self._card_visible_value, reverse=True)
        for amount in range(1, max_cards + 1):
            add(high_cards[:amount])

        by_rank: dict[str, list] = {}
        by_suit: dict[str, list] = {}
        for card in hand:
            by_rank.setdefault(str(getattr(card, "rank", "")), []).append(card)
            by_suit.setdefault(str(getattr(card, "suit", "")), []).append(card)

        rank_groups = sorted(
            by_rank.values(),
            key=lambda cards: (
                len(cards),
                sum(self._card_visible_value(c) for c in cards),
            ),
            reverse=True,
        )
        for cards in rank_groups:
            if len(cards) >= 2:
                add(sorted(cards, key=self._card_visible_value, reverse=True)[:4])

        pairs = [cards for cards in rank_groups if len(cards) >= 2]
        triples = [cards for cards in rank_groups if len(cards) >= 3]
        if len(pairs) >= 2:
            add(pairs[0][:2] + pairs[1][:2])
        if triples:
            pair = next((cards for cards in pairs if cards is not triples[0]), None)
            if pair is not None:
                add(triples[0][:3] + pair[:2])

        # Flushes and straights are generated directly from rank/suit maps.
        for cards in by_suit.values():
            if len(cards) >= 5:
                add(sorted(cards, key=self._card_visible_value, reverse=True)[:5])

        add(self._best_straight_cards(hand))
        for cards in by_suit.values():
            add(self._best_straight_cards(cards))

        projection_limit = min(
            self._MAX_CHILD_PROJECTED_PLAYS,
            max(3, max(1, play_limit) * 3),
        )
        ranked = sorted(
            candidates.values(),
            key=self._direct_child_play_priority,
            reverse=True,
        )
        return ranked[:projection_limit]

    def _child_discard_candidates(self, state):
        """Construct one deterministic low-value discard for each redraw size."""
        hand = list(getattr(state, "hand", ()))
        if not hand:
            return []
        max_cards = min(self.action_generator.MAX_SELECTED_CARDS, len(hand))
        low_cards = sorted(hand, key=self._card_visible_value)
        return [
            BalatroAction(DISCARD_CARDS, cards=low_cards[:amount])
            for amount in range(1, max_cards + 1)
        ]

    def _direct_child_play_priority(self, action):
        hand = self.evaluator.hand_evaluator.evaluate(action.cards)
        scoring = self.evaluator.scorer.scoring_cards(hand, action.cards)
        visible_chips = sum(self._card_visible_value(card) for card in scoring)
        return (
            self._HAND_STRENGTH.get(hand.value, -1),
            visible_chips,
            len(scoring),
            -len(action.cards),
        )

    def _best_straight_cards(self, cards):
        best_by_value = {}
        for card in cards:
            value = self.evaluator.RANK_ORDER.get(str(getattr(card, "rank", "")))
            if value is None:
                continue
            current = best_by_value.get(value)
            if (
                current is None
                or self._card_visible_value(card) > self._card_visible_value(current)
            ):
                best_by_value[value] = card

        sequences = ([14, 5, 4, 3, 2],) + tuple(
            list(range(high, high - 5, -1)) for high in range(14, 5, -1)
        )
        for sequence in sequences:
            if all(value in best_by_value for value in sequence):
                return [best_by_value[value] for value in sequence]
        return []

    def _card_visible_value(self, card) -> float:
        value = float(self.evaluator.scorer.card_chip_value(card))
        if getattr(card, "enhancement", None):
            value += 30.0
        if getattr(card, "edition", None):
            value += 25.0
        if getattr(card, "seal", None):
            value += 20.0
        return value

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

        top_hand = self.evaluator.hand_evaluator.evaluate(top.cards)
        top_core = self._scoring_core(top_hand, top.cards)
        max_cards = min(
            self.action_generator.MAX_SELECTED_CARDS,
            len(getattr(state, "hand", [])),
        )

        # A longer play with the same scoring core can act as a free redraw of
        # otherwise non-scoring cards. Keep one representative per card count.
        for amount in range(len(top.cards) + 1, max_cards + 1):
            variants = []
            for action in plays:
                if len(action.cards) != amount:
                    continue
                hand = self.evaluator.hand_evaluator.evaluate(action.cards)
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

    def _diverse_discard_beam(self, state, discards, limit: int):
        if limit <= 0 or not discards:
            return []

        ranked = sorted(
            discards,
            key=lambda action: self._discard_priority(state, action),
            reverse=True,
        )
        chosen = []
        chosen_keys = set()
        max_cards = min(
            self.action_generator.MAX_SELECTED_CARDS,
            len(getattr(state, "hand", [])),
        )

        # Redrawing 1 card and redrawing 4 cards are strategically different even
        # when a retained-structure heuristic ranks several 1-card choices higher.
        for amount in range(1, max_cards + 1):
            same_size = [action for action in discards if len(action.cards) == amount]
            if not same_size:
                continue
            best = max(
                same_size,
                key=lambda action: self._discard_priority(state, action),
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
        hand = self.evaluator.hand_evaluator.evaluate(action.cards)
        scoring_ids = set(self._scoring_core(hand, action.cards))
        cycled = [card for card in action.cards if id(card) not in scoring_ids]
        cycle_cost = sum(self._cycle_cost(card) for card in cycled)
        return (
            retained_structure,
            -cycle_cost,
            self._play_priority(state, action),
        )

    def _scoring_core(self, hand, cards) -> tuple[int, ...]:
        scoring = self.evaluator.scorer.scoring_cards(hand, cards)
        return tuple(sorted(id(card) for card in scoring))

    def _cycle_cost(self, card) -> float:
        cost = float(self.evaluator.scorer.card_chip_value(card))
        enhancement = getattr(card, "enhancement", None)
        edition = getattr(card, "edition", None)
        seal = getattr(card, "seal", None)
        if enhancement:
            cost += 30.0
        if enhancement in {"Steel", "Gold"}:
            cost += 30.0
        if edition:
            cost += 25.0
        if seal:
            cost += 20.0
        return cost

    @staticmethod
    def _action_identity(action) -> tuple[int, ...]:
        return tuple(sorted(id(card) for card in action.cards))
