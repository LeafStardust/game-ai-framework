from __future__ import annotations

from copy import deepcopy

from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.joker import JokerContext


class LiveDiscardJokerProjector:
    """Project exact deterministic Joker effects caused by one visible discard."""

    ACTIVE_CLASS_NAMES = frozenset(
        {
            "FacelessJoker",
            "MailInRebateJoker",
        }
    )

    def project(self, state, cards):
        if state is None:
            return None

        branch_state = state.copy()
        branch_state.jokers = deepcopy(list(getattr(state, "jokers", [])))
        discarded = list(cards or [])
        context = JokerContext(
            state=branch_state,
            cards=discarded,
            trigger="DISCARD",
            event=BalatroEvent(BalatroEventType.CARDS_DISCARDED, discarded),
            data={"hand_rules": hand_rules_for_state(branch_state)},
        )
        for joker in branch_state.jokers:
            if type(joker).__name__ in self.ACTIVE_CLASS_NAMES:
                context = joker.apply(context)
        return branch_state
