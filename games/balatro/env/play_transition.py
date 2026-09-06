"""Exact narrow Play lifecycle for Phase R4.

This owner intentionally admits only deterministic Red Deck / White Stake slices
whose action-time semantics are already exact: ordinary Small/Big blinds and the
narrow The Tooth Boss path, with an unmodified base playing-card deck and no
Joker, Tag, consumable, Voucher, random card, or other unowned callbacks. The
boundary can widen only when those source-order mechanics have canonical
environment owners.
"""

from __future__ import annotations

from collections.abc import Iterable

from games.balatro.blinds.blind import BlindType
from games.balatro.env.boss_play import (
    apply_tooth_press_play_economy_from_played_pile,
)
from games.balatro.env.deal import draw_one_supported_card_to_hand
from games.balatro.env.round_zones import (
    normalize_visible_card_indices,
    require_exact_selecting_hand_zones,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.scoring import BalatroScorer


_VANILLA_RANKS = frozenset({"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"})
_VANILLA_SUITS = frozenset({"Clubs", "Diamonds", "Hearts", "Spades"})
_VANILLA_IDENTITIES = frozenset(
    (rank, suit)
    for rank in _VANILLA_RANKS
    for suit in _VANILLA_SUITS
)


def _require_exact_int(name: str, value: object, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HeadlessTransitionError(f"{name} must be an exact integer")
    if value < minimum:
        raise HeadlessTransitionError(f"{name} must be at least {minimum}")
    return value


def _require_plain_base_cards(run: HeadlessRunState) -> None:
    order = run.require_playing_card_order()
    identities = [(card.rank, card.suit) for card in order]
    if (
        len(identities) != 52
        or len(set(identities)) != 52
        or set(identities) != _VANILLA_IDENTITIES
    ):
        raise HeadlessTransitionError(
            "R4 baseline Play currently requires the unmodified base-card composition"
        )

    for card in order:
        if (
            card.enhancement is not None
            or card.edition is not None
            or card.seal is not None
            or card.permanent_bonus != 0
            or card.debuffed
            or card.forced_selection
            or card.face_down
        ):
            raise HeadlessTransitionError(
                "R4 baseline Play does not yet own modified/debuffed/forced/face-down card effects"
            )


def _is_tooth_context(state) -> bool:
    return (
        getattr(state.blind, "type", None) == BlindType.BOSS
        and str(getattr(state, "boss_name", "") or "") == "The Tooth"
    )


def _require_supported_context(run: HeadlessRunState) -> None:
    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError("R4 baseline Play requires SELECTING_HAND phase")
    if state.blind is None:
        raise HeadlessTransitionError("R4 baseline Play requires an active blind")

    blind_type = getattr(state.blind, "type", None)
    boss_name = str(getattr(state, "boss_name", "") or "")
    ordinary = blind_type in {BlindType.SMALL, BlindType.BIG} and not boss_name
    tooth = blind_type == BlindType.BOSS and boss_name == "The Tooth"
    if not ordinary and not tooth:
        raise HeadlessTransitionError(
            "R4 baseline Play currently supports Small/Big blinds and The Tooth only"
        )
    if getattr(state.blind, "modifiers", None):
        raise HeadlessTransitionError(
            "R4 baseline Play does not yet own additional blind modifiers"
        )
    if bool(getattr(state.blind, "disabled", False)):
        raise HeadlessTransitionError("R4 baseline Play requires an active blind")
    if getattr(state.blind, "tag_key", None) is not None:
        raise HeadlessTransitionError("R4 baseline Play does not yet own blind-tag callbacks")
    if state.jokers:
        raise HeadlessTransitionError("R4 baseline Play does not yet own Joker callbacks")
    if run.tags:
        raise HeadlessTransitionError("R4 baseline Play does not yet own Tag callbacks")
    if state.consumables:
        raise HeadlessTransitionError(
            "R4 baseline Play does not yet own held consumable scoring interactions"
        )
    if state.vouchers:
        raise HeadlessTransitionError(
            "R4 baseline Play does not yet own Voucher action-time interactions"
        )
    if state.hand_size != 8:
        raise HeadlessTransitionError(
            "R4 baseline Play currently requires the ordinary Red Deck hand size"
        )

    _require_exact_int("score", state.score)
    _require_exact_int("hands_remaining", state.hands_remaining, minimum=1)
    requirement = _require_exact_int(
        "blind requirement",
        getattr(state.blind, "requirement", None),
    )
    if requirement < 0:
        raise HeadlessTransitionError("blind requirement cannot be negative")

    require_exact_selecting_hand_zones(run)
    _require_plain_base_cards(run)


def _increment_hand_counter(mapping: dict, hand_name: str, *, label: str) -> None:
    if not isinstance(mapping, dict):
        raise HeadlessTransitionError(f"{label} must be an exact mapping")
    current = mapping.get(hand_name)
    _require_exact_int(f"{label}[{hand_name}]", current)
    mapping[hand_name] = current + 1


def apply_supported_ordinary_play(
    run: HeadlessRunState,
    card_indices: Iterable[int],
) -> HeadlessRunState:
    """Apply one exact admitted Play through clear, loss, or deterministic redraw.

    ``card_indices`` are zero-based visible-hand positions. The input run and RNG
    are never mutated. A cleared blind stops at the established headless
    ``ROUND_EVAL`` boundary with zones still distributed; R2 cash-out owns later
    round-end repopulation. A failed final hand stops at ``GAME_OVER``. Otherwise
    the retained physical draw order refills the visible hand exactly.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    _require_supported_context(run)
    state = run.public
    indices = normalize_visible_card_indices(card_indices, hand_size=len(state.hand))

    next_run = run.copy()
    next_state = next_run.public
    selected = [next_state.hand[index] for index in indices]
    selected_ids = {id(card) for card in selected}

    # Vanilla spends the hand before moving highlighted cards into G.play.
    next_state.hands_remaining -= 1
    next_state.hand = [
        card for card in next_state.hand if id(card) not in selected_ids
    ]
    next_run.played_pile.extend(selected)

    # Permanent Ante history is written immediately on hand->play movement.
    for card in selected:
        card.played_this_ante = True
        card.played_this_ante_observed = True

    poker_hand = HandEvaluator().evaluate(selected)
    hand_name = poker_hand.value
    _increment_hand_counter(
        next_state.hand_play_counts,
        hand_name,
        label="hand_play_counts",
    )
    _increment_hand_counter(
        next_state.round_hand_play_counts,
        hand_name,
        label="round_hand_play_counts",
    )
    hand_level = next_state.hand_levels.get(hand_name)
    _require_exact_int(f"hand_levels[{hand_name}]", hand_level, minimum=1)
    if hand_name not in next_state.visible_poker_hands:
        next_state.visible_poker_hands = (
            *next_state.visible_poker_hands,
            hand_name,
        )
    next_state.last_played_hand = hand_name

    # Pinned vanilla calls Blind:press_play() here, after hand/counter history is
    # committed but before evaluate_play(). Only The Tooth is currently admitted
    # because its complete deterministic action-time mutation is canonically owned.
    if _is_tooth_context(next_state):
        next_run = apply_tooth_press_play_economy_from_played_pile(next_run)
        next_state = next_run.public
        selected = list(next_run.played_pile)

    hand_score = BalatroScorer().score(
        poker_hand,
        state=next_state,
        cards=selected,
        include_card_chips=True,
        resolve_random_effects=False,
    )
    next_state.score += hand_score.total

    # The admitted slice has no destruction or after-scoring callbacks, so every
    # played card survives and moves from G.play to the discard tail in play order.
    next_run.discard_pile.extend(next_run.played_pile)
    next_state.discard_pile.extend(next_run.played_pile)
    next_run.played_pile.clear()

    requirement = int(next_state.blind.requirement)
    if next_state.score >= requirement:
        next_state.phase = "ROUND_EVAL"
        return next_run

    if next_state.hands_remaining < 1:
        next_state.phase = "GAME_OVER"
        return next_run

    missing = next_state.hand_size - len(next_state.hand)
    if missing > len(next_run.draw_pile):
        raise HeadlessTransitionError(
            "R4 baseline Play does not yet own deck-exhaustion redraw semantics"
        )
    while len(next_run.public.hand) < next_run.public.hand_size:
        next_run = draw_one_supported_card_to_hand(next_run)

    return next_run
