"""Exact Tarot/Planet identity selection for ordinary main-shop cards.

This owns only ``get_current_pool(type, ..., 'sho')`` position reconstruction and
its subsequent ``pseudorandom_element``/resample sequence. Dynamic eligibility is
supplied by an authoritative caller; profile unlocks, bans, Showman state, pool
flags, and Planet softlocks are never guessed here.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from games.balatro.env.consumable_centers import current_consumable_pool_from_eligible_keys
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import shop_generation_vouchers_are_exact


@dataclass(frozen=True)
class ShopConsumableCenterPoll:
    run: HeadlessRunState
    card_type: str
    center_key: str
    resamples: int


def poll_base_shop_consumable_center(
    run: HeadlessRunState,
    card_type: str,
    eligible_keys: Collection[str],
) -> ShopConsumableCenterPoll:
    """Select one source-exact ordinary Tarot or Planet shop identity.

    Vanilla ``get_current_pool`` returns pool key ``Tarotsho{ante}`` or
    ``Planetsho{ante}``. Ineligible source positions remain ``UNAVAILABLE``;
    landing on one retries using ``..._resample2``, ``..._resample3``, etc.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("consumable shop generation requires active SHOP")
    if type(state.ante) is not int or state.ante < 1:
        raise HeadlessTransitionError("consumable shop generation requires positive exact Ante")
    if not shop_generation_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "base consumable generation does not own current voucher modifiers"
        )
    if run.tags:
        raise HeadlessTransitionError("base consumable generation does not own active Tag effects")
    if any((state.shop_jokers, state.shop_consumables, state.shop_boosters, state.shop_vouchers)):
        raise HeadlessTransitionError("base consumable generation requires ungenerated inventory")
    if card_type not in ("Tarot", "Planet"):
        raise HeadlessTransitionError("ordinary consumable type must be Tarot or Planet")

    try:
        pool = current_consumable_pool_from_eligible_keys(card_type, eligible_keys)
    except (TypeError, ValueError) as exc:
        raise HeadlessTransitionError("invalid authoritative consumable generation pool") from exc

    next_run = run.copy()
    pool_key = f"{card_type}sho{state.ante}"
    index = next_run.rng.pseudorandom_element_index(len(pool), pool_key)
    center = pool[index]
    source_it = 1
    resamples = 0
    while center == "UNAVAILABLE":
        source_it += 1
        resamples += 1
        index = next_run.rng.pseudorandom_element_index(
            len(pool),
            f"{pool_key}_resample{source_it}",
        )
        center = pool[index]

    return ShopConsumableCenterPoll(
        run=next_run,
        card_type=card_type,
        center_key=center,
        resamples=resamples,
    )
