"""Exact narrow Play lifecycle for Phase R4.

This owner intentionally admits only deterministic Red Deck / White Stake slices
whose action-time semantics are already exact: ordinary Small/Big blinds and the
narrow Psychic / Tooth / Hook / Pillar / Arm / Fish / Mouth / Needle / Manacle /
Verdant Leaf Boss paths, with an unmodified base playing-card deck and no Joker,
Tag, random-card, or other unowned callbacks. Held profile Tarot/Planet cards
and already-applied supported Vouchers are explicit play-time no-ops.
The boundary can widen only when those source-order mechanics have canonical
environment owners.
"""

from __future__ import annotations

from collections.abc import Iterable

from games.balatro.blinds.blind import BlindType
from games.balatro.boss_trigger import (
    boss_hand_is_debuffed,
    record_accepted_boss_hand,
)
from games.balatro.env.boss_debuffs import require_pillar_history_debuff_state
from games.balatro.env.boss_facing import draw_fish_post_play_cards
from games.balatro.env.boss_hand import apply_arm_debuff_hand_level
from games.balatro.env.boss_play import (
    apply_hook_press_play_discards_from_played_pile,
    apply_tooth_press_play_economy_from_played_pile,
)
from games.balatro.env.boss_resources import require_active_manacle_state
from games.balatro.env.consumable_centers import (
    VANILLA_PLANET_CENTER_ORDER,
    VANILLA_TAROT_CENTER_ORDER,
)
from games.balatro.env.deal import draw_one_supported_card_to_hand
from games.balatro.env.joker_sale import require_verdant_leaf_debuff_state
from games.balatro.env.round_zones import (
    normalize_visible_card_indices,
    require_exact_selecting_hand_zones,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    EXACT_ANTE_VOUCHER_KEYS,
    EXACT_DISCOUNT_VOUCHER_KEYS,
    EXACT_EDITION_RATE_VOUCHER_KEYS,
    EXACT_INTEREST_CAP_VOUCHER_KEYS,
    EXACT_REROLL_COST_VOUCHER_KEYS,
    EXACT_RESOURCE_VOUCHER_KEYS,
    EXACT_SHOP_SIZE_VOUCHER_KEYS,
    EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS,
)
from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.consumable import PlanetCard, TarotCard
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.scoring import BalatroScorer


_VANILLA_RANKS = frozenset({"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"})
_VANILLA_SUITS = frozenset({"Clubs", "Diamonds", "Hearts", "Spades"})
_VANILLA_IDENTITIES = frozenset(
    (rank, suit)
    for rank in _VANILLA_RANKS
    for suit in _VANILLA_SUITS
)
_PLAY_TIME_NO_EFFECT_VOUCHERS = (
    EXACT_RESOURCE_VOUCHER_KEYS
    | EXACT_EDITION_RATE_VOUCHER_KEYS
    | EXACT_DISCOUNT_VOUCHER_KEYS
    | EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS
    | EXACT_REROLL_COST_VOUCHER_KEYS
    | EXACT_INTEREST_CAP_VOUCHER_KEYS
    | EXACT_SHOP_SIZE_VOUCHER_KEYS
    | EXACT_ANTE_VOUCHER_KEYS
)
_PLAY_TIME_NO_EFFECT_CONSUMABLE_CENTERS = {
    "Tarot": frozenset(VANILLA_TAROT_CENTER_ORDER),
    "Planet": frozenset(VANILLA_PLANET_CENTER_ORDER),
}


def _require_exact_int(name: str, value: object, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HeadlessTransitionError(f"{name} must be an exact integer")
    if value < minimum:
        raise HeadlessTransitionError(f"{name} must be at least {minimum}")
    return value


def _is_play_time_no_effect_consumable(item: object) -> bool:
    if isinstance(item, (PlanetCard, TarotCard)):
        return True
    if type(item) is not GeneratedShopConsumableItem:
        return False

    centers = _PLAY_TIME_NO_EFFECT_CONSUMABLE_CENTERS.get(item.card_type)
    return (
        centers is not None
        and type(item.center_key) is str
        and item.center_key in centers
        and type(item.base_cost) is int
        and item.base_cost >= 0
        and type(item.price) is int
        and item.price >= 0
        and (item.discovered is None or type(item.discovered) is bool)
    )


def _require_plain_base_cards(
    run: HeadlessRunState,
    *,
    allow_pillar_history_debuffs: bool,
    allow_fish_facing: bool,
    allow_verdant_leaf_debuffs: bool,
) -> None:
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
            or card.forced_selection
        ):
            raise HeadlessTransitionError(
                "R4 baseline Play does not yet own modified/debuffed/forced/face-down card effects"
            )

    if not allow_fish_facing:
        if any(card.face_down for card in order):
            raise HeadlessTransitionError(
                "R4 baseline Play does not yet own modified/debuffed/forced/face-down card effects"
            )
    else:
        hand_ids = {id(card) for card in run.public.hand}
        if any(not card.facing_observed for card in run.public.hand):
            raise HeadlessTransitionError(
                "Fish Play requires authoritative current-hand facing state"
            )
        if any(
            card.face_down
            and (not card.facing_observed or id(card) not in hand_ids)
            for card in order
        ):
            raise HeadlessTransitionError(
                "Fish Play encountered face-down state outside the current hand"
            )

    if allow_verdant_leaf_debuffs:
        require_verdant_leaf_debuff_state(run)
        return

    if not allow_pillar_history_debuffs:
        if any(card.debuffed for card in order):
            raise HeadlessTransitionError(
                "R4 baseline Play does not yet own modified/debuffed/forced/face-down card effects"
            )
        return

    require_pillar_history_debuff_state(run)


def _boss_name(state) -> str:
    return str(getattr(state, "boss_name", "") or "")


def _is_tooth_context(state) -> bool:
    return (
        getattr(state.blind, "type", None) == BlindType.BOSS
        and _boss_name(state) == "The Tooth"
    )


def _is_hook_context(state) -> bool:
    return (
        getattr(state.blind, "type", None) == BlindType.BOSS
        and _boss_name(state) == "The Hook"
    )


def _is_arm_context(state) -> bool:
    return (
        getattr(state.blind, "type", None) == BlindType.BOSS
        and _boss_name(state) == "The Arm"
    )


def _is_fish_context(state) -> bool:
    return (
        getattr(state.blind, "type", None) == BlindType.BOSS
        and _boss_name(state) == "The Fish"
    )


def _require_supported_context(run: HeadlessRunState) -> None:
    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError("R4 baseline Play requires SELECTING_HAND phase")
    if state.blind is None:
        raise HeadlessTransitionError("R4 baseline Play requires an active blind")

    blind_type = getattr(state.blind, "type", None)
    boss_name = _boss_name(state)
    ordinary = blind_type in {BlindType.SMALL, BlindType.BIG} and not boss_name
    supported_boss = blind_type == BlindType.BOSS and boss_name in {
        "The Psychic",
        "The Tooth",
        "The Hook",
        "The Pillar",
        "The Arm",
        "The Fish",
        "The Mouth",
        "The Needle",
        "The Manacle",
        "Verdant Leaf",
    }
    if not ordinary and not supported_boss:
        raise HeadlessTransitionError(
            "R4 baseline Play currently supports Small/Big blinds, The Psychic, The Tooth, The Hook, The Pillar, The Arm, The Fish, The Mouth, The Needle, The Manacle, and Verdant Leaf only"
        )
    if boss_name == "The Manacle":
        require_active_manacle_state(run)
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
    if any(not _is_play_time_no_effect_consumable(item) for item in state.consumables):
        raise HeadlessTransitionError(
            "R4 baseline Play does not own this held consumable scoring interaction"
        )
    if any(key not in _PLAY_TIME_NO_EFFECT_VOUCHERS for key in state.vouchers):
        raise HeadlessTransitionError(
            "R4 baseline Play does not yet own Voucher action-time interactions"
        )
    if boss_name != "The Manacle" and state.hand_size != 8:
        raise HeadlessTransitionError(
            "R4 baseline Play currently requires the ordinary Red Deck hand size"
        )
    if boss_name == "The Mouth":
        if state.boss_blind_state_observed is not True:
            raise HeadlessTransitionError(
                "Mouth Play requires authoritative mutable Boss state"
            )
        only_hand = state.boss_blind_only_hand
        if only_hand is not None and only_hand not in state.hand_levels:
            raise HeadlessTransitionError(
                "Mouth Play requires a canonical locked hand"
            )
    if boss_name == "The Needle":
        if state.round_reset_hands_observed is not True:
            raise HeadlessTransitionError(
                "Needle Play requires authoritative round-reset hands"
            )
        reset_hands = state.round_reset_hands
        if (
            isinstance(reset_hands, bool)
            or not isinstance(reset_hands, int)
            or reset_hands < 0
            or run.boss_hands_sub != reset_hands - 1
            or run.boss_discards_sub is not None
            or run.boss_hand_size_sub is not None
        ):
            raise HeadlessTransitionError(
                "Needle Play requires its exact stored hands adjustment"
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
    _require_plain_base_cards(
        run,
        allow_pillar_history_debuffs=(
            blind_type is BlindType.BOSS and boss_name == "The Pillar"
        ),
        allow_fish_facing=(
            blind_type is BlindType.BOSS and boss_name == "The Fish"
        ),
        allow_verdant_leaf_debuffs=(
            blind_type is BlindType.BOSS and boss_name == "Verdant Leaf"
        ),
    )


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

    # Pinned vanilla moves highlighted cards to G.play facing up. This reveals
    # Fish-hidden identities to mechanics before hand classification while the
    # policy only ever saw their masked public observation.
    if _is_fish_context(next_state):
        for card in selected:
            card.face_down = False
            card.facing_observed = True

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
    # committed but before evaluate_play(). Admit only Boss mutations with exact
    # canonical owners at this source-order boundary.
    if _is_tooth_context(next_state):
        next_run = apply_tooth_press_play_economy_from_played_pile(next_run)
        next_state = next_run.public
        selected = list(next_run.played_pile)
    elif _is_hook_context(next_state):
        next_run = apply_hook_press_play_discards_from_played_pile(next_run)
        next_state = next_run.public
        selected = list(next_run.played_pile)

    hand_scores_zero = False
    if _is_arm_context(next_state):
        # Arm's debuff_hand trigger is a persistent level mutation, not a
        # whole-hand scoring debuff. Vanilla applies it immediately before the
        # ordinary score reads that hand level.
        next_run = apply_arm_debuff_hand_level(next_run, hand_name)
        next_state = next_run.public
        selected = list(next_run.played_pile)
    else:
        boss_hand = boss_hand_is_debuffed(next_state, poker_hand, selected)
        if not boss_hand.resolvable:
            raise HeadlessTransitionError(
                "R4 baseline Play cannot resolve the active Boss hand constraint"
            )
        hand_scores_zero = boss_hand.triggered
    if not hand_scores_zero:
        record_accepted_boss_hand(next_state, poker_hand)
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
    if _is_fish_context(next_state):
        return draw_fish_post_play_cards(next_run)
    while len(next_run.public.hand) < next_run.public.hand_size:
        next_run = draw_one_supported_card_to_hand(next_run)

    return next_run
