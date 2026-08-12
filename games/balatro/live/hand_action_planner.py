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
    """

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

        plays = self.action_generator.generate_play_actions(state)
        guaranteed_clears = [
            action
            for action in plays
            if self.evaluator.project_play(state, action).clears_blind
        ]
        if guaranteed_clears:
            return sorted(
                guaranteed_clears,
                key=lambda action: self._play_priority(state, action),
                reverse=True,
            )[: max(0, play_limit)]

        ranked_plays = self._diverse_play_beam(state, plays, play_limit)

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
