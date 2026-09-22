"""Exact headless tactical transitions for Phase R4.

The strategic environment deliberately does not expose card-level Play/Discard
choices to the learner. This module owns the exact simulator side of those
choices as they are admitted. Source-order Play lifecycle ownership lives in
``play_transition``; this module keeps the production decision-engine bridge and
the narrow exact Discard owner.
"""

from __future__ import annotations

from collections.abc import Iterable

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import BlindType
from games.balatro.env.boss_facing import draw_fish_post_discard_cards
from games.balatro.env.boss_resources import require_active_manacle_state
from games.balatro.env.boss_selection import BOSS_KEY_BY_NAME
from games.balatro.env.deal import draw_one_supported_card_to_hand
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.round_zones import (
    normalize_visible_card_indices,
    require_exact_selecting_hand_zones,
)
from games.balatro.env.tactical_evidence import (
    PublicTacticalTransitionEvidence,
    build_public_tactical_transition_evidence,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


# Pinned vanilla has no direct Blind callback in
# ``discard_cards_from_highlighted``. These Bosses also use the ordinary
# capacity-limited draw after a discard. Fish is included because its existing
# post-discard owner proves that ``prepped`` is clear and makes the replacement
# cards face up. House is ordinary after ``discards_used`` advances. Serpent,
# Wheel, Mark, and Cerulean Bell have distinct redraw behavior and remain
# fail-closed here until that behavior is composed at this boundary. Water
# removes every current discard at blind start, so no legal discard exists.
_ORDINARY_DISCARD_BOSS_NAMES = frozenset(BOSS_KEY_BY_NAME) - {
    "The Manacle",
    "The Psychic",
    "The Water",
    "The Serpent",
    "The Wheel",
    "The Mark",
    "Cerulean Bell",
}


def _require_active_ordinary_discard_boss_state(run: HeadlessRunState) -> None:
    """Require an audited Boss whose post-discard draw is ordinary."""
    state = run.public
    blind = state.blind
    if (
        state.boss_name not in _ORDINARY_DISCARD_BOSS_NAMES
        or blind is None
        or getattr(blind, "type", None) is not BlindType.BOSS
        or bool(getattr(blind, "disabled", False))
    ):
        raise HeadlessTransitionError(
            "ordinary Boss discard requires an active audited Boss blind"
        )
    if (
        getattr(blind, "modifiers", None)
        or getattr(blind, "tag_key", None) is not None
    ):
        raise HeadlessTransitionError(
            "ordinary Boss discard does not own additional blind modifiers"
        )
    if (
        state.hand_size != 8
        or run.boss_hands_sub is not None
        or run.boss_discards_sub is not None
        or run.boss_hand_size_sub is not None
    ):
        raise HeadlessTransitionError(
            "ordinary Boss discard requires ordinary Red Deck resource state"
        )
    if state.boss_name in {"The Eye", "The Mouth"}:
        if state.boss_blind_state_observed is not True:
            raise HeadlessTransitionError(
                "mutable-rule Boss discard requires authoritative Boss state"
            )
        if state.boss_name == "The Eye" and not isinstance(
            state.boss_blind_hands, set
        ):
            raise HeadlessTransitionError(
                "Eye discard requires authoritative used-hand state"
            )
        if (
            state.boss_name == "The Mouth"
            and state.boss_blind_only_hand is not None
            and state.boss_blind_only_hand not in state.hand_levels
        ):
            raise HeadlessTransitionError(
                "Mouth discard requires a canonical locked hand"
            )


def _require_active_psychic_discard_state(run: HeadlessRunState) -> None:
    """Require Psychic's exact ordinary-discard Red/White state."""
    state = run.public
    blind = state.blind
    if (
        state.boss_name != "The Psychic"
        or blind is None
        or getattr(blind, "type", None) is not BlindType.BOSS
        or bool(getattr(blind, "disabled", False))
    ):
        raise HeadlessTransitionError(
            "Psychic discard requires its active Boss blind"
        )
    if (
        getattr(blind, "modifiers", None)
        or getattr(blind, "tag_key", None) is not None
    ):
        raise HeadlessTransitionError(
            "Psychic discard does not own additional blind modifiers"
        )
    if (
        state.hand_size != 8
        or run.boss_hands_sub is not None
        or run.boss_discards_sub is not None
        or run.boss_hand_size_sub is not None
    ):
        raise HeadlessTransitionError(
            "Psychic discard requires ordinary Red Deck resource state"
        )


def _require_baseline_discard_callbacks_exact(run: HeadlessRunState) -> None:
    state = run.public
    if state.boss_name == "The Manacle":
        require_active_manacle_state(run)
    elif state.boss_name == "The Psychic":
        _require_active_psychic_discard_state(run)
    elif state.boss_name in _ORDINARY_DISCARD_BOSS_NAMES:
        _require_active_ordinary_discard_boss_state(run)
    elif state.boss_name is not None:
        raise HeadlessTransitionError(
            "R4 baseline discard does not yet own boss discard callbacks/redraw semantics for "
            f"{state.boss_name!r}"
        )
    if state.jokers:
        raise HeadlessTransitionError(
            "R4 baseline discard does not yet own Joker discard callbacks"
        )


def apply_supported_tactical_discard(
    run: HeadlessRunState,
    card_indices: Iterable[int],
) -> HeadlessRunState:
    """Apply one exact baseline Discard and redraw from retained physical order.

    ``card_indices`` are zero-based positions in the currently visible hand. The
    input state is never mutated. This R4 slice admits source-audited ordinary
    Boss redraw behavior, Fish's explicit face-up post-discard draw, The Psychic,
    and The Manacle's exact active hand-size reduction. It rejects unowned Boss
    redraws, every Joker discard callback, and Purple-seal generation.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError("tactical discard requires SELECTING_HAND phase")
    if state.discards_remaining <= 0:
        raise HeadlessTransitionError("tactical discard requires a remaining discard")
    if (
        isinstance(state.discards_used, bool)
        or not isinstance(state.discards_used, int)
        or state.discards_used < 0
    ):
        raise HeadlessTransitionError(
            "tactical discard requires authoritative discards_used"
        )

    indices = normalize_visible_card_indices(card_indices, hand_size=len(state.hand))
    _require_baseline_discard_callbacks_exact(run)
    require_exact_selecting_hand_zones(run)

    selected = [state.hand[index] for index in indices]
    if any(str(getattr(card, "seal", "") or "").upper() == "PURPLE" for card in selected):
        raise HeadlessTransitionError(
            "R4 baseline discard does not yet own Purple Seal generation"
        )

    next_run = run.copy()
    next_state = next_run.public
    next_selected = [next_state.hand[index] for index in indices]
    selected_ids = {id(card) for card in next_selected}

    # Vanilla discard callbacks fire before movement. All callback-producing
    # identities admitted above are absent, so the exact remaining movement is
    # hand-area order -> discard tail.
    next_state.hand = [card for card in next_state.hand if id(card) not in selected_ids]
    next_run.discard_pile.extend(next_selected)
    next_state.discard_pile.extend(next_selected)
    next_state.discards_remaining -= 1
    next_state.discards_used += 1

    # Normal non-Serpent redraw fills the hand to capacity from the retained
    # physical deck tail. Each primitive draw also restores vanilla hand sort and
    # canonicalizes the public deck without exposing hidden draw order.
    if next_state.boss_name == "The Fish":
        next_run = draw_fish_post_discard_cards(next_run)
    else:
        while len(next_run.public.hand) < next_run.public.hand_size and next_run.draw_pile:
            next_run = draw_one_supported_card_to_hand(next_run)

    return next_run


def _selected_observation_indices(observation, action: BalatroAction) -> tuple[int, ...]:
    selected = list(getattr(action, "cards", ()) or ())
    if not selected:
        raise HeadlessTransitionError("tactical decision returned no selected cards")

    hand = list(observation.hand)
    positions = {id(card): index for index, card in enumerate(hand)}
    try:
        indices = tuple(positions[id(card)] for card in selected)
    except KeyError as exc:
        raise HeadlessTransitionError(
            "tactical decision selected a card outside its public observation"
        ) from exc
    return normalize_visible_card_indices(indices, hand_size=len(hand))


def _planned_tactical_decision(run: HeadlessRunState, decision_engine):
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if run.public.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "planned tactical step requires SELECTING_HAND phase"
        )

    decide_method = getattr(decision_engine, "decide", None)
    if not callable(decide_method):
        raise TypeError("decision_engine must provide decide(state)")

    observation = public_observation_state(run.public)
    decision = decide_method(observation)
    action = getattr(decision, "action", None)
    if not isinstance(action, BalatroAction):
        raise HeadlessTransitionError(
            "tactical decision engine did not return BalatroAction"
        )
    return observation, action


def _apply_decided_tactical_action(
    run: HeadlessRunState,
    observation,
    action: BalatroAction,
) -> HeadlessRunState:
    indices = _selected_observation_indices(observation, action)
    if action.name == DISCARD_CARDS:
        return apply_supported_tactical_discard(run, indices)
    if action.name == PLAY_CARDS:
        return apply_supported_ordinary_play(run, indices)
    raise HeadlessTransitionError(
        f"tactical decision engine returned unsupported action {action.name!r}"
    )


def apply_planned_tactical_step(run: HeadlessRunState, decision_engine) -> HeadlessRunState:
    """Decide from one policy-safe observation and execute one admitted tactical step.

    R4 intentionally calls the same production-shaped ``decide(state)`` boundary
    used by the live hand-action engine. The returned decision must carry the
    canonical ``BalatroAction`` in ``decision.action``. The same sanitized
    observation object is used both for decision input and for mapping selected
    card objects back to visible positions. No hidden card identity or physical
    draw order is supplied to the decision engine.
    """
    observation, action = _planned_tactical_decision(run, decision_engine)
    return _apply_decided_tactical_action(run, observation, action)


def apply_planned_tactical_step_with_evidence(
    run: HeadlessRunState,
    decision_engine,
) -> tuple[HeadlessRunState, PublicTacticalTransitionEvidence]:
    """Execute one admitted tactical step and return public-safe R4 evidence.

    The decision engine is invoked exactly once. Evidence reuses that exact
    sanitized decision observation and canonical action, then sanitizes the
    public post-state. Simulator-private zones and RNG remain only on the returned
    ``HeadlessRunState`` and are never copied into the evidence object.
    """
    observation, action = _planned_tactical_decision(run, decision_engine)
    result = _apply_decided_tactical_action(run, observation, action)
    evidence = build_public_tactical_transition_evidence(
        observation,
        action,
        result.public,
    )
    return result, evidence
