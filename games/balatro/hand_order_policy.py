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
    """Reorder a chosen play when card-order-sensitive scoring improves."""

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
        current_key = self._projection_key(current_projection)
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
            key = self._projection_key(projection)
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
                "place the best scoring trigger first before committing the play",
                f"guaranteed score {current_projection.hand_score} -> "
                f"{best_projection.hand_score}",
                f"expected score {current_projection.expected_hand_score:.3f} -> "
                f"{best_projection.expected_hand_score:.3f}",
            ),
        )

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
