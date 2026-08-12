from __future__ import annotations

from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


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

    Root Play candidates remain exhaustive so a visible guaranteed blind clear is
    never hidden by search optimization. Recursive hypothetical states first use
    a deterministic public-state-only shortlist grouped by poker hand and selected
    card count, then run the expensive Joker/score projection only on those
    representatives. This keeps child beam construction bounded without using
    hidden draw order or mutating authoritative state.
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
    _MAX_CHILD_PROJECTED_PLAYS = 10

    def __init__(self, *args, **kwargs):
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

        # Candidate construction can inspect the same Play several times: once
        # for terminal-clear detection, again for ranking, and again while
        # preserving redraw-size diversity. Cache only for this one state/beam;
        # recursive search states get a fresh cache so hypothetical states are
        # never retained for the lifetime of the whole search.
        previous_cache = self._play_projection_cache
        self._play_projection_cache = {}
        try:
            plays = self.action_generator.generate_play_actions(state)

            # rank_plans()/plan() construct the root beam before the first search
            # node is consumed. Keep that visible root exhaustive. Recursive child
            # beams have already consumed at least one node, so only they use the
            # cheap deterministic shortlist.
            root_beam = self.nodes_evaluated == 0
            projected_plays = (
                plays
                if root_beam
                else self._shortlist_child_plays(state, plays, play_limit)
            )

            guaranteed_clears = [
                action
                for action in projected_plays
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
                projected_plays,
                play_limit,
            )

            if (
                not allow_discards
                or discard_limit <= 0
                or int(getattr(state, "discards_remaining", 0)) <= 0
            ):
                return ranked_plays

            discards = self.action_generator.generate_discard_actions(state)
            ranked_discards = self._diverse_discard_beam(
                state,
                discards,
                discard_limit,
            )
            return ranked_plays + ranked_discards
        finally:
            self._play_projection_cache = previous_cache

    def _shortlist_child_plays(self, state, plays, play_limit: int):
        """Keep a hard-bounded diverse set before expensive child projection.

        All visible subsets receive only a cheap poker-hand/chip key. The returned
        set first preserves one representative for each selected-card count, then
        adds distinct poker-hand categories and finally the strongest remaining
        cheap candidates. Expensive Joker/score projection is therefore capped at
        five candidates for the normal one-wide child beam and ten for wider child
        beams. No retained-structure scan or Joker transition projection occurs in
        this prefilter.
        """
        if not plays:
            return []

        projection_limit = min(
            self._MAX_CHILD_PROJECTED_PLAYS,
            max(5, max(1, play_limit) * 5),
        )
        metadata = []
        for action in plays:
            hand = self.evaluator.hand_evaluator.evaluate(action.cards)
            metadata.append(
                (
                    action,
                    hand,
                    self._cheap_play_priority(state, action, hand),
                )
            )

        chosen = []
        chosen_keys = set()

        def add_best(candidates) -> None:
            if not candidates or len(chosen) >= projection_limit:
                return
            action, _hand, _priority = max(candidates, key=lambda item: item[2])
            identity = self._action_identity(action)
            if identity in chosen_keys:
                return
            chosen.append(action)
            chosen_keys.add(identity)

        max_cards = min(
            self.action_generator.MAX_SELECTED_CARDS,
            len(getattr(state, "hand", [])),
        )
        for amount in range(1, max_cards + 1):
            add_best([item for item in metadata if len(item[0].cards) == amount])

        hand_values = sorted(
            {item[1].value for item in metadata},
            key=lambda value: self._HAND_STRENGTH.get(value, -1),
            reverse=True,
        )
        for value in hand_values:
            add_best([item for item in metadata if item[1].value == value])
            if len(chosen) >= projection_limit:
                return chosen

        for action, _hand, _priority in sorted(
            metadata,
            key=lambda item: item[2],
            reverse=True,
        ):
            identity = self._action_identity(action)
            if identity in chosen_keys:
                continue
            chosen.append(action)
            chosen_keys.add(identity)
            if len(chosen) >= projection_limit:
                break
        return chosen

    def _cheap_play_priority(self, state, action, hand):
        del state
        scoring = self.evaluator.scorer.scoring_cards(hand, action.cards)
        visible_chips = sum(
            float(self.evaluator.scorer.card_chip_value(card))
            for card in scoring
        )
        scoring_ids = {id(card) for card in scoring}
        cycled = [card for card in action.cards if id(card) not in scoring_ids]
        cycle_cost = sum(self._cycle_cost(card) for card in cycled)
        return (
            self._HAND_STRENGTH.get(hand.value, -1),
            visible_chips,
            len(scoring),
            -cycle_cost,
            -len(action.cards),
        )

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
