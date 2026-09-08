"""Policy-facing sanitization for canonical Balatro observations.

Headless mechanics may need true identities and physical orders that Balatro is
currently hiding from the player. Those facts must not cross the environment
observation boundary.
"""

from __future__ import annotations

from copy import copy
from enum import Enum
from typing import Any

from games.balatro.card import BalatroCard
from games.balatro.state import BalatroState


_UNKNOWN_CARD_VALUE = "?"
_AMBER_HIDDEN_PHASES = frozenset({"DRAW_TO_HAND", "SELECTING_HAND"})
_AMBER_PRIVATE_JOKER_FIELDS = frozenset({"live_id", "area_index"})


def _canonical_public_value(value: Any):
    """Return a stable comparison value for already-public Joker model state."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return (type(value).__name__, value.value)
    if isinstance(value, dict):
        return tuple(
            sorted(
                (str(key), _canonical_public_value(item))
                for key, item in value.items()
            )
        )
    if isinstance(value, (list, tuple)):
        return tuple(_canonical_public_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted(repr(_canonical_public_value(item)) for item in value))
    # Modeled Joker fields are expected to be primitive/container state. If a
    # future model stores another gameplay object, collapse it to its type rather
    # than leaking an address-dependent repr into the public ordering key.
    return ("object", type(value).__name__)


def _joker_public_fingerprint(joker: Any) -> tuple:
    values = vars(joker) if hasattr(joker, "__dict__") else {}
    return (
        type(joker).__name__,
        tuple(
            sorted(
                (
                    str(name),
                    _canonical_public_value(value),
                )
                for name, value in values.items()
                if name not in _AMBER_PRIVATE_JOKER_FIELDS
            )
        ),
    )


def _amber_order_is_hidden(state: BalatroState) -> bool:
    blind = getattr(state, "blind", None)
    return (
        state.boss_name == "Amber Acorn"
        and state.phase in _AMBER_HIDDEN_PHASES
        and blind is not None
        and not bool(getattr(blind, "disabled", False))
    )


def _public_jokers(state: BalatroState) -> list:
    """Return policy-safe Joker objects for the current visible ordering state.

    During active Amber Acorn the player knows the owned Joker multiset but not
    the shuffled identity-to-position mapping. Canonicalizing by visible model
    state prevents the simulator's hidden physical permutation from leaking.
    Engine ``sort_id``/area identity is stripped as well. Once Amber is disabled,
    normal visible physical order is returned again.
    """
    jokers = list(state.jokers)
    if not _amber_order_is_hidden(state):
        return [copy(joker) for joker in jokers]

    masked = []
    for joker in jokers:
        clone = copy(joker)
        if hasattr(clone, "live_id"):
            clone.live_id = None
        if hasattr(clone, "area_index"):
            clone.area_index = None
        masked.append(clone)
    return sorted(masked, key=_joker_public_fingerprint)


def public_observation_state(state: BalatroState) -> BalatroState:
    """Return an isolated policy observation with hidden identities/orders masked.

    A face-down hand card remains represented as one hand position with
    ``face_down=True``. Rank, suit, modifiers, stable physical id, debuff state,
    and permanent-card metadata are deliberately withheld because any of them can
    reveal the hidden card's identity. Forced-selection remains visible because
    it is an explicit controller constraint the player can see.

    During active Amber Acorn, the Joker multiset remains visible but its hidden
    physical permutation does not. The source state is never mutated.
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
    observation.jokers = _public_jokers(state)
    return observation
