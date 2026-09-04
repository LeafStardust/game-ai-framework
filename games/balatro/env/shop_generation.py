"""Exact first R2 slice of normal shop inventory generation.

Vanilla ``create_card_for_shop`` first chooses a card *type* with the keyed
``cdt{ante}`` pseudorandom stream. Concrete center selection is a separate and
substantially wider boundary involving profile unlocks, rarity/pools, editions,
vouchers and duplicate rules. This module deliberately owns only the base
Red/White type poll and does not manufacture a shop item identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_BASE_SHOP_RATES: tuple[tuple[str, float], ...] = (
    ("Joker", 20.0),
    ("Tarot", 4.0),
    ("Planet", 4.0),
    ("Base", 0.0),
    ("Spectral", 0.0),
)


@dataclass(frozen=True)
class ShopCardTypePoll:
    """One exact type poll plus the isolated successor RNG state."""

    run: HeadlessRunState
    card_type: str


def _shop_type_from_polled_rate(polled_rate: float) -> str:
    """Map vanilla's weighted ``polled_rate`` to its first matching shop type."""
    if isinstance(polled_rate, bool) or not isinstance(polled_rate, (int, float)):
        raise TypeError("polled_rate must be numeric")

    total_rate = sum(rate for _, rate in _BASE_SHOP_RATES)
    value = float(polled_rate)
    if value <= 0.0 or value > total_rate:
        raise ValueError("polled_rate is outside the base shop rate range")

    check_rate = 0.0
    for card_type, rate in _BASE_SHOP_RATES:
        # Vanilla's exact test is:
        #   polled_rate > check_rate and polled_rate <= check_rate + v.val
        if value > check_rate and value <= check_rate + rate:
            return card_type
        check_rate += rate

    # ``pseudorandom`` is strictly inside this positive-rate envelope for the
    # live path. Keep malformed/direct calls fail closed anyway.
    raise ValueError("polled_rate did not resolve to a positive-rate shop type")


def poll_base_shop_card_type(run: HeadlessRunState) -> ShopCardTypePoll:
    """Poll one source-exact base shop card type without choosing an identity.

    This boundary is intentionally restricted to the ordinary unmodified shop
    rates initialized by vanilla for a normal run:

    ``Joker=20, Tarot=4, Planet=4, Playing Card=0, Spectral=0``.

    Vouchers and active Tags are rejected because they can alter shop rates,
    card type, slots, price, edition or creation behavior. Concrete item identity
    generation remains unavailable after this function returns.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("base shop type poll requires an active SHOP")
    if not isinstance(state.ante, int) or isinstance(state.ante, bool) or state.ante < 1:
        raise HeadlessTransitionError("base shop type poll requires a positive exact Ante")
    if state.vouchers:
        raise HeadlessTransitionError("base shop type poll does not own voucher-modified rates")
    if run.tags:
        raise HeadlessTransitionError("base shop type poll does not own active Tag shop effects")

    # This primitive begins at the same ungenerated-shop boundary used by the
    # current cash-out owners. It never overwrites already-materialized inventory.
    if any(
        (
            state.shop_jokers,
            state.shop_consumables,
            state.shop_boosters,
            state.shop_vouchers,
        )
    ):
        raise HeadlessTransitionError("base shop type poll requires ungenerated inventory")

    next_run = run.copy()
    total_rate = sum(rate for _, rate in _BASE_SHOP_RATES)
    polled_rate = next_run.rng.random(f"cdt{state.ante}") * total_rate
    return ShopCardTypePoll(
        run=next_run,
        card_type=_shop_type_from_polled_rate(polled_rate),
    )
