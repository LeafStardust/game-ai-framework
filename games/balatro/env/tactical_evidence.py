"""Public-information-safe tactical transition evidence for Phase R4.

The record intentionally contains only policy-visible state plus the canonical
Balatro action chosen from that state. Simulator-private draw order, retained
zone authority, RNG state, and hidden card identity never cross this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.round_zones import normalize_visible_card_indices
from games.balatro.env.transition import HeadlessTransitionError
from games.balatro.state import BalatroState


@dataclass(frozen=True)
class PublicTacticalTransitionEvidence:
    """One public pre-action/action/post-action tactical transition.

    ``selected_hand_indices`` are stable zero-based positions in ``before.hand``.
    ``action`` remains the canonical ``BalatroAction``; its card objects are the
    corresponding policy-safe cards owned by ``before`` rather than simulator
    card objects.
    """

    before: BalatroState
    action: BalatroAction
    selected_hand_indices: tuple[int, ...]
    after: BalatroState


def _selected_public_indices(
    observation: BalatroState,
    action: BalatroAction,
) -> tuple[int, ...]:
    if action.name not in {PLAY_CARDS, DISCARD_CARDS}:
        raise HeadlessTransitionError(
            f"tactical evidence does not support action {action.name!r}"
        )
    if action.target is not None:
        raise HeadlessTransitionError(
            "tactical evidence does not own non-card action targets"
        )

    selected = list(action.cards or ())
    if not selected:
        raise HeadlessTransitionError("tactical evidence requires selected cards")

    positions = {id(card): index for index, card in enumerate(observation.hand)}
    try:
        raw_indices = tuple(positions[id(card)] for card in selected)
    except KeyError as exc:
        raise HeadlessTransitionError(
            "tactical evidence action selected a card outside the public observation"
        ) from exc
    return normalize_visible_card_indices(raw_indices, hand_size=len(observation.hand))


def build_public_tactical_transition_evidence(
    before_observation: BalatroState,
    action: BalatroAction,
    after_state: BalatroState,
) -> PublicTacticalTransitionEvidence:
    """Build an isolated public-safe evidence record for one admitted hand action.

    ``before_observation`` must be the same policy observation from which
    ``action`` was chosen. The selected positions are resolved before cloning so
    object identity is used only at this local decision boundary; the resulting
    record is stable across simulator/live object copies through visible indices.
    Both stored states pass through the canonical public-observation sanitizer.
    """
    if not isinstance(before_observation, BalatroState):
        raise TypeError("before_observation must be BalatroState")
    if not isinstance(action, BalatroAction):
        raise TypeError("action must be BalatroAction")
    if not isinstance(after_state, BalatroState):
        raise TypeError("after_state must be BalatroState")

    indices = _selected_public_indices(before_observation, action)
    before = public_observation_state(before_observation)
    after = public_observation_state(after_state)
    safe_action = BalatroAction(
        action.name,
        cards=[before.hand[index] for index in indices],
    )
    return PublicTacticalTransitionEvidence(
        before=before,
        action=safe_action,
        selected_hand_indices=indices,
        after=after,
    )
