"""Exact first R2 slices of normal shop inventory generation.

Vanilla ``create_card_for_shop`` first chooses a card *type* with the keyed
``cdt{ante}`` pseudorandom stream. Joker slots then roll rarity with
``rarity{ante}sho`` before constructing/culling the concrete center pool.
Concrete identity selection is a wider boundary involving profile unlocks,
used-center/Showman state, Ante gates, Planet softlocks, editions and vouchers.
This module deliberately stops before that pool/identity boundary.
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
_BASE_MAIN_SHOP_SLOTS = 2


@dataclass(frozen=True)
class ShopCardTypePoll:
    run: HeadlessRunState
    card_type: str


@dataclass(frozen=True)
class ShopMainTypeSequence:
    run: HeadlessRunState
    card_types: tuple[str, str]


@dataclass(frozen=True)
class ShopJokerRarityPoll:
    run: HeadlessRunState
    rarity: int


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
        if value > check_rate and value <= check_rate + rate:
            return card_type
        check_rate += rate

    raise ValueError("polled_rate did not resolve to a positive-rate shop type")


def _joker_rarity_from_roll(roll: float) -> int:
    """Map vanilla's ordinary Joker rarity roll to rarity id 1/2/3."""
    if isinstance(roll, bool) or not isinstance(roll, (int, float)):
        raise TypeError("rarity roll must be numeric")
    value = float(roll)
    if value < 0.0 or value > 1.0:
        raise ValueError("rarity roll must be within [0, 1]")
    return 3 if value > 0.95 else 2 if value > 0.7 else 1


def _validate_base_shop_boundary(run: HeadlessRunState) -> None:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("base shop generation requires an active SHOP")
    if not isinstance(state.ante, int) or isinstance(state.ante, bool) or state.ante < 1:
        raise HeadlessTransitionError("base shop generation requires a positive exact Ante")
    if state.vouchers:
        raise HeadlessTransitionError("base shop generation does not own voucher modifiers")
    if run.tags:
        raise HeadlessTransitionError("base shop generation does not own active Tag shop effects")
    if any(
        (
            state.shop_jokers,
            state.shop_consumables,
            state.shop_boosters,
            state.shop_vouchers,
        )
    ):
        raise HeadlessTransitionError("base shop generation requires ungenerated inventory")


def poll_base_shop_card_type(run: HeadlessRunState) -> ShopCardTypePoll:
    """Poll one source-exact base shop card type without choosing an identity."""
    _validate_base_shop_boundary(run)

    next_run = run.copy()
    total_rate = sum(rate for _, rate in _BASE_SHOP_RATES)
    polled_rate = next_run.rng.random(f"cdt{run.public.ante}") * total_rate
    return ShopCardTypePoll(next_run, _shop_type_from_polled_rate(polled_rate))


def poll_base_main_shop_types(run: HeadlessRunState) -> ShopMainTypeSequence:
    """Poll the exact two normal main-shop slot types in source order.

    Vanilla initializes ``G.GAME.shop.joker_max = 2`` and calls
    ``create_card_for_shop(G.shop_jokers)`` once per missing main-shop slot.
    Booster and voucher areas are distinct generation paths and remain unowned.
    """
    _validate_base_shop_boundary(run)

    next_run = run.copy()
    card_types: list[str] = []
    total_rate = sum(rate for _, rate in _BASE_SHOP_RATES)
    for _ in range(_BASE_MAIN_SHOP_SLOTS):
        polled_rate = next_run.rng.random(f"cdt{run.public.ante}") * total_rate
        card_types.append(_shop_type_from_polled_rate(polled_rate))

    return ShopMainTypeSequence(next_run, (card_types[0], card_types[1]))


def poll_base_shop_joker_rarity(run: HeadlessRunState) -> ShopJokerRarityPoll:
    """Poll ordinary shop Joker rarity before concrete pool construction.

    ``create_card_for_shop`` calls ``create_card(..., key_append='sho')``. For a
    Joker, vanilla ``get_current_pool`` therefore consumes
    ``pseudorandom('rarity' .. ante .. 'sho')`` and maps it to Common/Uncommon/
    Rare ids 1/2/3. Legendary rarity is not reachable through this ordinary path.
    """
    _validate_base_shop_boundary(run)

    next_run = run.copy()
    roll = next_run.rng.random(f"rarity{run.public.ante}sho")
    return ShopJokerRarityPoll(next_run, _joker_rarity_from_roll(roll))
