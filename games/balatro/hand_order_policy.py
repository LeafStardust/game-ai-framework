from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations

from games.balatro.actions import PLAY_CARDS, REORDER_HAND, BalatroAction
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


_ORDER_SENSITIVE_JOKERS = frozenset(
    {
        "HangingChadJoker",
        "PhotographJoker",
    }
)


@dataclass(frozen=True)
class HandOrderDecision:
    permutation: tuple[int, ...]
    current_guaranteed_score: int
    ordered_guaranteed_score: int
    current_expected_score: float
    ordered_expected_score: float
    rationale: tuple[str, ...]

    def to_action(self) -> BalatroAction:
        return BalatroAction(REORDER_HAND, target=self.permutation)


class HandOrderPolicy:
    """Reorder a chosen play when card-order-sensitive scoring improves.

    First-played-card mechanics are execution constraints, not ordinary score noise.
    If a selected card is live and another selected card is debuffed, an active
    first-card retrigger engine must never place the debuffed card first merely
    because the projection layer ties or incompletely models the retrigger.
    """

    def recommend(
        self,
        state,
        action: BalatroAction,
        *,
        evaluator: LiveHandDecisionEvaluator | None = None,
    ) -> HandOrderDecision | None:
        if str(getattr(state, "phase", "")) != "SELECTING_HAND":
            return None
        if str(getattr(action, "name", "")) != PLAY_CARDS:
            return None
        selected = tuple(getattr(action, "cards", ()))
        if len(selected) < 2 or not self._has_order_sensitive_joker(state):
            return None

        evaluator = evaluator or LiveHandDecisionEvaluator()
        current_projection = evaluator.project_play(state, action)
        current_key = self._order_key(selected, current_projection)
        best_order = selected
        best_projection = current_projection
        best_key = current_key

        for ordered in permutations(selected):
            if ordered == selected:
                continue
            projection = evaluator.project_play(
                state,
                BalatroAction(PLAY_CARDS, cards=list(ordered)),
            )
            key = self._order_key(ordered, projection)
            if key > best_key:
                best_order = ordered
                best_projection = projection
                best_key = key

        if best_order == selected:
            return None
        permutation = self._full_hand_permutation(state, selected, best_order)
        if permutation is None or permutation == tuple(range(len(permutation))):
            return None
        return HandOrderDecision(
            permutation=permutation,
            current_guaranteed_score=int(current_projection.hand_score),
            ordered_guaranteed_score=int(best_projection.hand_score),
            current_expected_score=float(current_projection.expected_hand_score),
            ordered_expected_score=float(best_projection.expected_hand_score),
            rationale=(
                "order-sensitive played-card scoring can be improved",
                "first-card retrigger authority prefers a live selected card over a debuffed selected card",
                "place the best scoring trigger first before committing the play",
                f"guaranteed score {current_projection.hand_score} -> "
                f"{best_projection.hand_score}",
                f"expected score {current_projection.expected_hand_score:.3f} -> "
                f"{best_projection.expected_hand_score:.3f}",
            ),
        )

    @classmethod
    def _order_key(cls, ordered, projection) -> tuple[float, ...]:
        # When at least one selected card is live, a live first card is mandatory
        # for first-card retrigger engines. This precedes ordinary projected score so
        # an incomplete/tied projection cannot put a disabled trigger first.
        any_live = any(not bool(getattr(card, "debuffed", False)) for card in ordered)
        first_live = not bool(getattr(ordered[0], "debuffed", False))
        live_first_authority = 1.0 if (not any_live or first_live) else 0.0
        return (live_first_authority, *cls._projection_key(projection))

    @staticmethod
    def _projection_key(projection) -> tuple[float, int, float, int]:
        return (
            float(getattr(projection, "clear_probability", 0.0)),
            int(getattr(projection, "hand_score", 0)),
            float(getattr(projection, "expected_hand_score", 0.0)),
            int(getattr(projection, "maximum_hand_score", 0)),
        )

    @staticmethod
    def _has_order_sensitive_joker(state) -> bool:
        return any(
            type(joker).__name__ in _ORDER_SENSITIVE_JOKERS
            and not bool(getattr(joker, "debuffed", False))
            for joker in getattr(state, "jokers", ())
        )

    @staticmethod
    def _full_hand_permutation(state, selected, ordered):
        hand = list(getattr(state, "hand", ()))
        selected_ids = {id(card) for card in selected}
        positions = [
            index
            for index, card in enumerate(hand)
            if id(card) in selected_ids
        ]
        if len(positions) != len(selected):
            return None

        desired = list(hand)
        for position, card in zip(positions, ordered):
            desired[position] = card
        index_by_id = {id(card): index for index, card in enumerate(hand)}
        try:
            return tuple(index_by_id[id(card)] for card in desired)
        except KeyError:
            return None
