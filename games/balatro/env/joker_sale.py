"""Exact fail-closed Joker-sale ownership for training and Verdant Leaf.

Vanilla selling a Joker removes it from the Joker area, runs the card's
``remove_from_deck`` inverse lifecycle, credits ``sell_cost``, and disables
Verdant Leaf. The headless shop boundary permits explicitly audited inventory-
only Jokers plus Juggler's hand-size inverse and Drunkard's persistent-discard
inverse. Other resource-sensitive and persistent-state Jokers remain fail-
closed until their inverse lifecycle is owned.
"""

from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    _EXACT_R1_JOKER_ACQUISITION_TYPES,
    _OWNED_DECK_SCORING_TYPES,
)
from games.balatro.env.joker_order import JokerOrderError
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.castle import CastleJoker
from games.balatro.jokers.rocket import RocketJoker
from games.balatro.jokers.vampire import VampireJoker


_STATIC_SELL_SAFE_TYPES = tuple(
    joker_type
    for joker_type in (
        *_EXACT_R1_JOKER_ACQUISITION_TYPES,
        *_OWNED_DECK_SCORING_TYPES,
        GoldenJoker,
        CastleJoker,
        RocketJoker,
        VampireJoker,
    )
    if joker_type is not JugglerJoker
)


def _validate_owned_joker_identity(
    run: HeadlessRunState,
    joker_index: int,
    *,
    allow_juggler: bool = False,
    allow_drunkard: bool = False,
) -> int:
    """Validate an owned Joker sale and return its exact sell value."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if isinstance(joker_index, bool) or not isinstance(joker_index, int):
        raise HeadlessTransitionError("joker index must be an exact integer")
    if joker_index < 0 or joker_index >= len(state.jokers):
        raise HeadlessTransitionError("joker index is out of range")
    if isinstance(state.money, bool) or not isinstance(state.money, int):
        raise HeadlessTransitionError("Joker sale requires exact integer money")

    joker = state.jokers[joker_index]
    owned_inverse = (
        type(joker) in _STATIC_SELL_SAFE_TYPES
        or (allow_juggler and type(joker) is JugglerJoker)
        or (allow_drunkard and type(joker) is DrunkardJoker)
    )
    if not owned_inverse:
        raise HeadlessTransitionError(
            "Joker sale inverse lifecycle is not exactly owned for this Joker"
        )
    if type(joker) is JugglerJoker and (
        type(state.hand_size) is not int or state.hand_size < 1
    ):
        raise HeadlessTransitionError(
            "Juggler sale requires exact positive hand size"
        )
    if type(joker) is DrunkardJoker:
        if state.round_reset_discards_observed is not True:
            raise HeadlessTransitionError(
                "Drunkard sale requires authoritative round-reset discards"
            )
        if (
            type(state.round_reset_discards) is not int
            or state.round_reset_discards < 1
        ):
            raise HeadlessTransitionError(
                "Drunkard sale requires exact positive round-reset discards"
            )
    if getattr(joker, "eternal", False):
        raise HeadlessTransitionError("Eternal Joker cannot be sold")
    if getattr(joker, "edition", None) is not None:
        raise HeadlessTransitionError("Joker editions remain fail-closed for sale")

    sell_cost = getattr(joker, "sell_cost", None)
    if isinstance(sell_cost, bool) or not isinstance(sell_cost, int) or sell_cost < 0:
        raise HeadlessTransitionError("Joker sale requires exact nonnegative sell_cost")
    if run.joker_order_state is not None:
        run.require_joker_order_state()
    return sell_cost


def _sell_owned_joker(
    run: HeadlessRunState,
    joker_index: int,
    sell_cost: int,
) -> HeadlessRunState:
    """Apply exact inverse state, inventory, and private-order removal."""
    next_run = run.copy()
    next_state = next_run.public
    sold = next_state.jokers[joker_index]
    if next_run.joker_order_state is not None:
        try:
            next_run.joker_order_state.remove(sold, next_state.jokers)
        except JokerOrderError as exc:
            raise HeadlessTransitionError(
                "cannot retain exact Joker order after sale"
            ) from exc
    next_state.money += sell_cost
    if type(sold) is JugglerJoker:
        next_state.hand_size -= 1
    elif type(sold) is DrunkardJoker:
        next_state.round_reset_discards -= 1
    next_state.jokers.pop(joker_index)
    if next_state.joker_generation_pool_observed:
        # Card:remove clears the sold center from G.GAME.used_jokers once no
        # copy remains in G.jokers. Reuse the canonical ordered-pool owner so
        # exact shop generation sees that center again after the sale.
        from games.balatro.env.shop_generation_state import (
            restore_removed_shop_jokers_to_generation_pool,
        )

        next_run = restore_removed_shop_jokers_to_generation_pool(
            next_run,
            (sold,),
        )
    return next_run


def validate_joker_sale_exact(run: HeadlessRunState, joker_index: int) -> None:
    """Validate the first exact strategic SELL_JOKER boundary.

    The initial training slice is deliberately limited to an active main shop
    and inventory-only Jokers. Pack-time sales and resource-sensitive inverse
    lifecycles remain unavailable until their complete transitions are owned.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if run.public.phase != "SHOP" or not run.public.shop_active:
        raise HeadlessTransitionError("exact SELL_JOKER requires active SHOP")
    _validate_owned_joker_identity(
        run,
        joker_index,
        allow_juggler=True,
        allow_drunkard=True,
    )


def can_sell_joker_exact(run: HeadlessRunState, joker_index: int) -> bool:
    """Return exact sale legality without mutating state or RNG."""
    try:
        validate_joker_sale_exact(run, joker_index)
    except (TypeError, HeadlessTransitionError):
        return False
    return True


def sell_joker_exact(run: HeadlessRunState, joker_index: int) -> HeadlessRunState:
    """Sell one audited Joker with an owned inverse during the active shop."""
    validate_joker_sale_exact(run, joker_index)
    sell_cost = _validate_owned_joker_identity(
        run,
        joker_index,
        allow_juggler=True,
        allow_drunkard=True,
    )

    return _sell_owned_joker(run, joker_index, sell_cost)


def _permanent_cards(run: HeadlessRunState) -> list[BalatroCard]:
    cards = run.require_playing_card_order()
    if not cards:
        raise HeadlessTransitionError("Verdant Leaf requires authoritative permanent cards")
    if any(not isinstance(card, BalatroCard) for card in cards):
        raise HeadlessTransitionError("Verdant Leaf permanent cards are malformed")
    return cards


def _require_verdant_all_card_debuff(run: HeadlessRunState) -> None:
    """Prove the exact active Verdant all-playing-card debuff boundary."""
    state = run.public
    if state.boss_name != "Verdant Leaf":
        raise HeadlessTransitionError("Verdant Leaf cleanup requires Verdant Leaf boss")
    if state.blind is None:
        raise HeadlessTransitionError("Verdant Leaf cleanup requires blind state")
    cards = _permanent_cards(run)
    if any(not card.debuffed for card in cards):
        raise HeadlessTransitionError(
            "Verdant Leaf cleanup requires the owned all-card debuff state"
        )


def require_verdant_leaf_debuff_state(run: HeadlessRunState) -> None:
    """Validate the canonical active all-playing-card debuff state."""
    _require_verdant_all_card_debuff(run)


def _clear_verdant_playing_cards(run: HeadlessRunState) -> HeadlessRunState:
    next_run = run.copy()
    for card in next_run.require_playing_card_order():
        card.debuffed = False
    return next_run


def apply_verdant_leaf_debuff(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror active Verdant Leaf debuffing every non-Joker playing card."""
    state = run.public
    if state.boss_name != "Verdant Leaf":
        raise HeadlessTransitionError("Verdant Leaf debuff requires Verdant Leaf boss")
    if state.blind is None:
        raise HeadlessTransitionError("Verdant Leaf requires active blind state")
    if getattr(state.blind, "disabled", False):
        raise HeadlessTransitionError("disabled Verdant Leaf cannot apply card debuffs")
    cards = _permanent_cards(run)
    if any(card.debuffed for card in cards):
        raise HeadlessTransitionError(
            "Verdant Leaf start requires clean pre-blind card debuff state"
        )

    next_run = run.copy()
    for card in next_run.require_playing_card_order():
        card.debuffed = True
    return next_run


def clear_verdant_leaf_defeat_debuff(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror normal ``Blind:defeat`` reset clearing Verdant card debuffs.

    Vanilla normal defeat eventually calls ``set_blind(nil, nil, true)``.  The
    blank reset blind re-evaluates every permanent playing card as non-debuffed,
    but this path is *not* a ``Blind:disable`` event and must not manufacture
    ``blind.disabled = true``.  Keep this distinct from sale/Chicot cleanup.
    """
    _require_verdant_all_card_debuff(run)
    if bool(getattr(run.public.blind, "disabled", False)):
        raise HeadlessTransitionError(
            "Verdant normal defeat cleanup requires an active, non-disabled blind"
        )
    return _clear_verdant_playing_cards(run)


def clear_verdant_leaf_debuff(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror disabled Verdant re-evaluating all permanent cards as non-debuffed.

    Vanilla ``Blind:disable`` sets ``self.disabled`` before calling
    ``debuff_card`` across playing cards. Verdant's disabled path therefore
    clears every playing-card debuff. Keep that inverse centralized so Chicot
    and the minimum Verdant sale lifecycle cannot diverge.
    """
    _require_verdant_all_card_debuff(run)

    next_run = _clear_verdant_playing_cards(run)
    next_run.public.blind.disabled = True
    return next_run


def sell_static_joker_during_verdant(
    run: HeadlessRunState,
    joker_index: int,
) -> HeadlessRunState:
    """Sell one exact inventory-only Joker and disable active Verdant Leaf.

    This is intentionally not the final general ``SELL_JOKER`` action owner.
    It establishes the exact mechanical boundary required by Verdant while the
    environment contract remains ``PLANNED``.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "Verdant Joker sale currently requires SELECTING_HAND phase"
        )
    if state.boss_name != "Verdant Leaf" or state.blind is None:
        raise HeadlessTransitionError("Verdant Joker sale requires active Verdant Leaf")
    if getattr(state.blind, "disabled", False):
        raise HeadlessTransitionError("Verdant Leaf is already disabled")
    sell_cost = _validate_owned_joker_identity(run, joker_index)

    cards = _permanent_cards(run)
    if any(not card.debuffed for card in cards):
        raise HeadlessTransitionError(
            "Verdant Joker sale requires active owned all-card debuff"
        )

    next_run = _sell_owned_joker(run, joker_index, sell_cost)
    return clear_verdant_leaf_debuff(next_run)
