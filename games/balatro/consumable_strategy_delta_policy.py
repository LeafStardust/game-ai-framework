from __future__ import annotations

"""Canonical strategic value for deterministic Tarot/Spectral card transforms.

The existing ContextualConsumableTargetEvaluator remains authoritative for support,
legality, target enumeration, literal/contextual card value, overwrite costs, and
all effect-specific safety rules. This policy reuses the consumable's real ``use``
method on a deep-copied public state, synchronizes any separately represented
persistent playing cards, and adds one conservative canonical ``StrategyDelta``
term to already-positive target evaluations.

Stochastic, generation, economy-only, Joker-targeted, and otherwise unsupported
consumables never enter this layer because the underlying evaluator fails closed for
them.
"""

import copy
from dataclasses import replace

from games.balatro.bonds.strategy_delta import strategy_delta_from_states
from games.balatro.build.consumable_targeting import (
    ConsumableTargetEvaluation,
    ContextualConsumableTargetEvaluator,
)
from games.balatro.consumable import Consumable, ConsumableContext


_CONSUMABLE_STRATEGY_WEIGHT = 0.10
_CARD_FIELDS = ("rank", "suit", "enhancement", "edition", "seal")


def _same_public_card(left, right) -> bool:
    left_live = getattr(left, "live_id", None)
    right_live = getattr(right, "live_id", None)
    if left_live is not None and right_live is not None:
        return left_live == right_live
    return left is right


def _find_persistent_card(state, source_card):
    owned = getattr(state, "owned_deck", None)
    if owned is None:
        return None

    live_id = getattr(source_card, "live_id", None)
    if live_id is not None:
        matches = [card for card in owned if getattr(card, "live_id", None) == live_id]
        return matches[0] if len(matches) == 1 else None

    # In deterministic/unit state the hand and owned_deck may intentionally share
    # object references. deepcopy preserves those aliases, so identity is enough.
    for card in owned:
        if card is source_card:
            return card
    return None


def _sync_transformed_cards_to_owned_deck(
    before_state,
    projected_state,
    target_indices: tuple[int, ...],
) -> bool:
    """Mirror exact transformed hand-card properties into persistent composition.

    Return False only when an authoritative owned_deck exists but a transformed
    target cannot be mapped unambiguously. That makes strategic projection fail
    closed rather than guessing which duplicate card changed.
    """
    if getattr(projected_state, "owned_deck", None) is None:
        return True

    for index in target_indices:
        if index < 0 or index >= len(before_state.hand) or index >= len(projected_state.hand):
            return False
        original = before_state.hand[index]
        transformed = projected_state.hand[index]
        persistent = _find_persistent_card(projected_state, transformed)
        if persistent is None:
            # A separate observed owned-deck object normally maps by live_id. If
            # the projected hand card itself is not enough, try the source live_id.
            persistent = _find_persistent_card(projected_state, original)
        if persistent is None:
            return False
        for field in _CARD_FIELDS:
            setattr(persistent, field, getattr(transformed, field))
    return True


def _project_target_state(state, consumable, target_indices: tuple[int, ...]):
    """Apply one exact public consumable target to a deep-copied state."""
    if not isinstance(consumable, Consumable):
        return None
    if not target_indices:
        return None

    projected = copy.deepcopy(state)
    projected_consumable = copy.deepcopy(consumable)
    try:
        cards = [projected.hand[index] for index in target_indices]
    except (IndexError, TypeError):
        return None

    context = ConsumableContext(state=projected, cards=cards)
    if not projected_consumable.can_use(context):
        return None

    before = [
        tuple(getattr(card, field) for field in _CARD_FIELDS)
        for card in cards
    ]
    try:
        projected_consumable.use(context)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return None

    # Destruction legitimately removes target cards from the projected hand. The
    # consumable's own shared destruction projector already updates owned_deck.
    name = str(getattr(consumable, "name", ""))
    if name != "The Hanged Man":
        if not _sync_transformed_cards_to_owned_deck(state, projected, target_indices):
            return None
        after_cards = [projected.hand[index] for index in target_indices]
        after = [
            tuple(getattr(card, field) for field in _CARD_FIELDS)
            for card in after_cards
        ]
        if before == after:
            return None

    return projected


def _strategy_adjustment(
    state,
    consumable,
    evaluation: ConsumableTargetEvaluation,
) -> tuple[float, tuple[str, ...]]:
    # Strategic structure cannot make a target with non-positive literal/contextual
    # value independently admissible. It only ranks already-viable exact targets.
    if float(evaluation.total_gain) <= 0.0:
        return 0.0, ()

    projected = _project_target_state(state, consumable, evaluation.target_indices)
    if projected is None:
        return 0.0, ()
    try:
        delta = strategy_delta_from_states(state, projected)
    except (AttributeError, KeyError, TypeError, ValueError):
        return 0.0, ()

    weighted = _CONSUMABLE_STRATEGY_WEIGHT * float(delta.value)
    if abs(weighted) <= 1e-12:
        return 0.0, ()
    return weighted, (
        f"canonical StrategyDelta={delta.value:+.3f}",
        f"raw BuildValue delta={delta.raw_delta:+.3f}",
        f"transition inertia={delta.transition_cost:.3f}",
        f"consumable strategy weight={_CONSUMABLE_STRATEGY_WEIGHT:.3f}",
        f"weighted strategic adjustment={weighted:+.3f}",
    )


def _adjust_evaluation(state, consumable, evaluation):
    adjustment, notes = _strategy_adjustment(state, consumable, evaluation)
    if not notes:
        return evaluation
    return replace(
        evaluation,
        total_gain=float(evaluation.total_gain) + adjustment,
        rationale=(
            *evaluation.rationale,
            *notes,
            "consumable legality and literal target value remain authoritative",
        ),
    )


def install_consumable_strategy_delta_policy() -> None:
    if getattr(
        ContextualConsumableTargetEvaluator,
        "_canonical_strategy_delta_installed",
        False,
    ):
        return

    original_rank_targets = ContextualConsumableTargetEvaluator.rank_targets

    def rank_targets(self, state, consumable):
        ranked = original_rank_targets(self, state, consumable)
        adjusted = [
            _adjust_evaluation(state, consumable, evaluation)
            for evaluation in ranked
        ]
        return self._sorted(adjusted)

    ContextualConsumableTargetEvaluator.rank_targets = rank_targets
    ContextualConsumableTargetEvaluator._canonical_strategy_delta_installed = True
