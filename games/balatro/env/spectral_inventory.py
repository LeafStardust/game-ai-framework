"""Exact held Spectral generation for Séance's admitted game profile."""

from dataclasses import dataclass, replace

from games.balatro.env.consumable_centers import REGULAR_SPECTRAL_CENTER_KEYS
from games.balatro.env.consumable_generation import poll_seance_spectral_center
from games.balatro.env.shop_pricing import vanilla_card_cost
from games.balatro.env.tag_selection import TagProfileState
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import expected_shop_discount_percent_for_vouchers


@dataclass(frozen=True, slots=True)
class GeneratedHeldSpectral:
    center_key: str
    price: int

    category = "SPECTRAL"
    base_cost = 4
    discovered = True

    def __post_init__(self) -> None:
        if not isinstance(self.center_key, str) or self.center_key not in REGULAR_SPECTRAL_CENTER_KEYS:
            raise HeadlessTransitionError("held Spectral requires an exact regular center")
        if type(self.price) is not int or self.price < 1:
            raise HeadlessTransitionError("held Spectral requires exact pricing")


def reprice_held_spectral(
    item: GeneratedHeldSpectral, *, inflation: int, discount_percent: int
) -> GeneratedHeldSpectral:
    return replace(item, price=vanilla_card_cost(
        item.base_cost,
        edition=None,
        inflation=inflation,
        discount_percent=discount_percent,
    ))


def require_seance_spectral_authority(run: HeadlessRunState) -> None:
    """Require the pinned Spectral profile and absence of unowned modifiers."""
    discovery = run.generation_discovery
    profile = run.tag_profile_state
    if discovery is None or profile is None or any(
        type(discovery.get(key)) is not bool
        or discovery[key] != (key in profile.discovered_center_keys)
        for key in REGULAR_SPECTRAL_CENTER_KEYS
    ):
        raise HeadlessTransitionError("Séance requires pristine-profile Spectral authority")
    if run.tags or any(type(joker).__name__ == "ShowmanJoker" for joker in run.public.jokers):
        raise HeadlessTransitionError("Séance pool modifiers are not owned")


def generate_seance_held_spectral(run: HeadlessRunState) -> None:
    """Generate and publish one Spectral on the caller's isolated play state."""
    state = run.public
    if type(state.consumable_slots) is not int or state.consumable_slots < 0:
        raise HeadlessTransitionError("Séance requires exact consumable capacity")
    if len(state.consumables) >= state.consumable_slots:
        return

    require_seance_spectral_authority(run)
    held = set()
    for item in state.consumables:
        if type(item) is GeneratedHeldSpectral:
            held.add(item.center_key)
        elif str(getattr(item, "category", getattr(item, "card_type", ""))).upper() not in {
            "TAROT", "PLANET",
        }:
            raise HeadlessTransitionError("Séance requires exact held consumable identities")

    discount = expected_shop_discount_percent_for_vouchers(state)
    if (
        discount is None
        or state.shop_discount_percent_observed is not True
        or type(state.shop_discount_percent) is not int
        or state.shop_discount_percent != discount
        or state.shop_inflation_observed is not True
    ):
        raise HeadlessTransitionError("Séance requires exact Spectral price inputs")
    price = vanilla_card_cost(
        GeneratedHeldSpectral.base_cost,
        edition=None,
        inflation=state.shop_inflation,
        discount_percent=discount,
    )
    center, _ = poll_seance_spectral_center(run.rng, state.ante, REGULAR_SPECTRAL_CENTER_KEYS - held)
    state.consumables.append(GeneratedHeldSpectral(center, price))
    run.generation_discovery[center] = True
    run.tag_profile_state = TagProfileState(run.tag_profile_state.discovered_center_keys | {center})
