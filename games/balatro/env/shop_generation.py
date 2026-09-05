"""Exact first R2 slices of normal shop inventory generation.

Vanilla ``create_card_for_shop`` first chooses a card *type* with the keyed
``cdt{ante}`` pseudorandom stream. Joker slots then roll rarity with
``rarity{ante}sho`` before constructing/culling the concrete center pool.
Concrete identity selection additionally depends on exact dynamic pool
eligibility. This module accepts that eligibility only when supplied explicitly;
it does not guess profile unlocks, duplicate suppression, bans or pool flags.

Ordinary Joker creation also rolls its edition inside the same vanilla
``create_card(..., key_append='sho')`` call. The base boundary below therefore
owns the exact ``edisho{ante}`` edition poll as a separate composable primitive;
Negative generation is modeled here without implying Negative acquisition is
training-safe.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from games.balatro.env.joker_centers import current_joker_pool_from_eligible_keys
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    expected_main_shop_slots_for_vouchers,
    shop_generation_vouchers_are_exact,
)
from games.balatro.state import BalatroState


@dataclass(frozen=True)
class ShopCardTypePoll:
    run: HeadlessRunState
    card_type: str


@dataclass(frozen=True)
class ShopMainTypeSequence:
    run: HeadlessRunState
    card_types: tuple[str, ...]


@dataclass(frozen=True)
class ShopJokerRarityPoll:
    run: HeadlessRunState
    rarity: int


@dataclass(frozen=True)
class ShopJokerCenterPoll:
    run: HeadlessRunState
    center_key: str
    rarity: int
    resamples: int


@dataclass(frozen=True)
class ShopJokerEditionPoll:
    run: HeadlessRunState
    edition: str | None


def _shop_rates_for_state(state: BalatroState) -> tuple[tuple[str, float], ...]:
    """Return vanilla normal-shop weights from exact canonical run state."""
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    tarot = state.tarot_rate
    planet = state.planet_rate
    for name, value in (("tarot_rate", tarot), ("planet_rate", planet)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HeadlessTransitionError(f"base shop {name} must be numeric")
        if float(value) < 0.0:
            raise HeadlessTransitionError(f"base shop {name} cannot be negative")
    return (
        ("Joker", 20.0),
        ("Tarot", float(tarot)),
        ("Planet", float(planet)),
        ("Base", 0.0),
        ("Spectral", 0.0),
    )


def _shop_type_from_polled_rate(
    polled_rate: float,
    rates: tuple[tuple[str, float], ...] | None = None,
) -> str:
    """Map vanilla's weighted ``polled_rate`` to its first matching shop type."""
    if isinstance(polled_rate, bool) or not isinstance(polled_rate, (int, float)):
        raise TypeError("polled_rate must be numeric")
    active_rates = rates or (
        ("Joker", 20.0),
        ("Tarot", 4.0),
        ("Planet", 4.0),
        ("Base", 0.0),
        ("Spectral", 0.0),
    )

    total_rate = sum(rate for _, rate in active_rates)
    value = float(polled_rate)
    if value <= 0.0 or value > total_rate:
        raise ValueError("polled_rate is outside the shop rate range")

    check_rate = 0.0
    for card_type, rate in active_rates:
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


def _joker_edition_from_roll(roll: float, edition_rate: float) -> str | None:
    """Map vanilla ``poll_edition`` for an ordinary shop Joker.

    This is the non-guaranteed, ``_mod=1``, Negative-allowed path used by
    ``create_card(..., key_append='sho')``. Source ordering is significant:
    Negative is tested first and is not scaled by ``G.GAME.edition_rate``;
    Polychrome, Holographic, and Foil are then tested cumulatively against the
    same single random draw.
    """
    if isinstance(roll, bool) or not isinstance(roll, (int, float)):
        raise TypeError("edition roll must be numeric")
    if isinstance(edition_rate, bool) or not isinstance(edition_rate, (int, float)):
        raise TypeError("edition_rate must be numeric")
    value = float(roll)
    rate = float(edition_rate)
    if value < 0.0 or value > 1.0:
        raise ValueError("edition roll must be within [0, 1]")
    if rate < 0.0:
        raise ValueError("edition_rate cannot be negative")

    if value > 1.0 - 0.003:
        return "Negative"
    if value > 1.0 - 0.006 * rate:
        return "Polychrome"
    if value > 1.0 - 0.02 * rate:
        return "Holographic"
    if value > 1.0 - 0.04 * rate:
        return "Foil"
    return None


def _validate_base_shop_boundary(run: HeadlessRunState) -> None:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("base shop generation requires an active SHOP")
    if not isinstance(state.ante, int) or isinstance(state.ante, bool) or state.ante < 1:
        raise HeadlessTransitionError("base shop generation requires a positive exact Ante")
    if not shop_generation_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "base shop generation does not own current voucher modifiers"
        )
    _shop_rates_for_state(state)
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
    rates = _shop_rates_for_state(run.public)
    total_rate = sum(rate for _, rate in rates)
    polled_rate = next_run.rng.random(f"cdt{run.public.ante}") * total_rate
    return ShopCardTypePoll(next_run, _shop_type_from_polled_rate(polled_rate, rates))


def poll_base_main_shop_types(run: HeadlessRunState) -> ShopMainTypeSequence:
    """Poll all normal main-shop slot types in source order.

    Vanilla starts Red Deck at two main-shop slots. Overstock and Overstock Plus
    each add one persistent slot, so the exact count is reconstructed from the
    authoritative used-Voucher history before RNG advances. Booster and Voucher
    areas are distinct generation paths and remain outside this type sequence.
    """
    _validate_base_shop_boundary(run)

    slot_count = expected_main_shop_slots_for_vouchers(run.public)
    if slot_count is None:
        raise HeadlessTransitionError("main shop slot count is not exact")

    next_run = run.copy()
    card_types: list[str] = []
    rates = _shop_rates_for_state(run.public)
    total_rate = sum(rate for _, rate in rates)
    for _ in range(slot_count):
        polled_rate = next_run.rng.random(f"cdt{run.public.ante}") * total_rate
        card_types.append(_shop_type_from_polled_rate(polled_rate, rates))

    return ShopMainTypeSequence(next_run, tuple(card_types))


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


def poll_base_shop_joker_center(
    run: HeadlessRunState,
    rarity: int,
    eligible_keys: Collection[str],
) -> ShopJokerCenterPoll:
    """Select one ordinary shop Joker identity from an exact eligible pool.

    This reproduces vanilla ``get_current_pool`` + ``pseudorandom_element``
    identity selection after the dynamic eligibility predicates have already
    been resolved by an authoritative owner. Ineligible rarity-pool positions
    remain literal ``UNAVAILABLE`` entries. If the first draw lands on one,
    vanilla retries with ``Joker{rarity}sho_resample2``, then ``...resample3``,
    and so on until an available center is selected.

    The function intentionally does not infer unlock/profile/Showman/ban/flag
    state and does not instantiate a runtime Joker object or roll an edition.
    """
    _validate_base_shop_boundary(run)
    if type(rarity) is not int or rarity not in (1, 2, 3):
        raise HeadlessTransitionError("ordinary shop Joker rarity must be exact 1, 2, or 3")

    pool = current_joker_pool_from_eligible_keys(rarity, eligible_keys)
    next_run = run.copy()
    pool_key = f"Joker{rarity}sho"

    index = next_run.rng.pseudorandom_element_index(len(pool), pool_key)
    center = pool[index]
    resamples = 0
    source_it = 1
    while center == "UNAVAILABLE":
        source_it += 1
        resamples += 1
        index = next_run.rng.pseudorandom_element_index(
            len(pool),
            f"{pool_key}_resample{source_it}",
        )
        center = pool[index]

    return ShopJokerCenterPoll(next_run, center, rarity, resamples)


def poll_base_shop_joker_edition(run: HeadlessRunState) -> ShopJokerEditionPoll:
    """Poll the exact edition assigned by ordinary base-shop Joker creation.

    The base boundary validates that current owned Vouchers and the canonical
    ``joker_generation_edition_rate`` agree exactly. Hone and Glow Up therefore
    remain safe here while changing the Foil/Holographic/Polychrome thresholds
    exactly as vanilla does. Negative remains unscaled by edition rate.
    """
    _validate_base_shop_boundary(run)
    rate = run.public.joker_generation_edition_rate
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        raise HeadlessTransitionError("base shop Joker edition rate must be numeric")
    exact_rate = float(rate)
    if exact_rate < 0.0:
        raise HeadlessTransitionError("base shop Joker edition rate cannot be negative")

    next_run = run.copy()
    roll = next_run.rng.random(f"edisho{run.public.ante}")
    return ShopJokerEditionPoll(
        next_run,
        _joker_edition_from_roll(roll, exact_rate),
    )
