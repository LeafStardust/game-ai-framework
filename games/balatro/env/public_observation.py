"""Policy-facing sanitization for canonical Balatro observations.

Headless mechanics may need the true identity of a physical card that Balatro is
currently rendering face down. That identity is hidden information and must not
cross the environment observation boundary.
"""

from __future__ import annotations

from copy import copy

from games.balatro.card import BalatroCard
from games.balatro.state import BalatroState


_UNKNOWN_CARD_VALUE = "?"


def public_observation_state(state: BalatroState) -> BalatroState:
    """Return an isolated policy observation with hidden hand identities masked.

    A face-down hand card remains represented as one hand position with
    ``face_down=True``. Rank, suit, modifiers, stable physical id, debuff state,
    and permanent-card metadata are deliberately withheld because any of them can
    reveal the hidden card's identity. Forced-selection remains visible because
    it is an explicit controller constraint the player can see.

    The source state is never mutated. Policy-visible hand cards are cloned even
    though the historical ``BalatroState.copy()`` helper shallow-copies card
    lists, so downstream observation consumers cannot mutate simulator-owned hand
    card objects by alias.
    """
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")

    observation = state.copy()
    masked_hand: list[BalatroCard] = []
    for card in observation.hand:
        if not card.face_down:
            masked_hand.append(copy(card))
            continue
        masked_hand.append(
            BalatroCard(
                rank=_UNKNOWN_CARD_VALUE,
                suit=_UNKNOWN_CARD_VALUE,
                live_id=None,
                forced_selection=card.forced_selection,
                face_down=True,
            )
        )
    observation.hand = masked_hand
    return observation
