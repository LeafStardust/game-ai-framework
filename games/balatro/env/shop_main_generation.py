"""Source-ordered exact generation for the two ordinary main-shop slots.

Vanilla calls ``create_card_for_shop(G.shop_jokers)`` once per missing slot and
immediately emplaces each result. Emplacement alone does not call ``add_to_deck``
or mutate ``G.GAME.used_jokers``, so it does not change slot-two pool eligibility.
The headless boundary can therefore keep publication atomic while preserving RNG
order: fully generate slot one, fully generate slot two, then publish both items.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.shop_consumable_generation_state import (
    eligible_consumable_records_from_state,
    generate_ordinary_shop_consumable_descriptor_from_state,
)
from games.balatro.env.shop_consumable_items import (
    GeneratedShopConsumableItem,
    insert_generated_shop_consumable_item,
    materialize_base_shop_consumable_descriptor,
)
from games.balatro.env.shop_generation import poll_base_shop_card_type
from games.balatro.env.shop_generation_state import eligible_joker_keys_from_state
from games.balatro.env.shop_items import (
    GeneratedShopJokerItem,
    insert_generated_shop_joker_item,
    materialize_shop_joker_descriptor,
)
from games.balatro.env.shop_joker_generation import generate_ordinary_shop_joker_descriptor
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    shop_generation_vouchers_are_exact,
    shop_pricing_vouchers_are_exact,
)


GeneratedMainShopItem = GeneratedShopJokerItem | GeneratedShopConsumableItem


@dataclass(frozen=True)
class GeneratedMainShop:
    run: HeadlessRunState
    items: tuple[GeneratedMainShopItem, GeneratedMainShopItem]


def _preflight_main_shop_generation(run: HeadlessRunState) -> None:
    """Validate every state source a two-slot base shop may consume before RNG."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("main shop generation requires active SHOP")
    if not shop_generation_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "main shop generation does not own current Voucher modifiers"
        )
    if run.tags:
        raise HeadlessTransitionError("main shop generation does not own active Tag modifiers")
    if any((state.shop_jokers, state.shop_consumables, state.shop_boosters, state.shop_vouchers)):
        raise HeadlessTransitionError("main shop generation requires ungenerated inventory")

    if not isinstance(state.shop_inflation_observed, bool) or not state.shop_inflation_observed:
        raise HeadlessTransitionError("shop inflation is not authoritative")
    if not isinstance(state.shop_discount_percent_observed, bool) or not state.shop_discount_percent_observed:
        raise HeadlessTransitionError("shop discount percent is not authoritative")
    if type(state.shop_inflation) is not int or state.shop_inflation < 0:
        raise HeadlessTransitionError("shop inflation must be a nonnegative exact integer")
    if (
        type(state.shop_discount_percent) is not int
        or state.shop_discount_percent < 0
        or state.shop_discount_percent > 100
    ):
        raise HeadlessTransitionError("shop discount percent must be an exact integer within 0..100")
    if not shop_pricing_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "main shop pricing does not match current Voucher ownership"
        )

    # Either slot may become any positive-rate type. Validate all candidate
    # canonical catalogues before the first cdt{ante} node advances.
    for rarity in (1, 2, 3, 4):
        eligible_joker_keys_from_state(run, rarity)
    eligible_consumable_records_from_state(run, "Tarot")
    eligible_consumable_records_from_state(run, "Planet")


def _generate_one_main_shop_item(
    run: HeadlessRunState,
) -> tuple[HeadlessRunState, GeneratedMainShopItem]:
    type_poll = poll_base_shop_card_type(run)
    if type_poll.card_type == "Joker":
        descriptor = generate_ordinary_shop_joker_descriptor(type_poll.run)
        return materialize_shop_joker_descriptor(descriptor)
    if type_poll.card_type in ("Tarot", "Planet"):
        descriptor = generate_ordinary_shop_consumable_descriptor_from_state(
            type_poll.run,
            type_poll.card_type,
        )
        return materialize_base_shop_consumable_descriptor(descriptor)
    raise HeadlessTransitionError(
        f"base main-shop type is not owned: {type_poll.card_type}"
    )


def generate_base_main_shop(run: HeadlessRunState) -> GeneratedMainShop:
    """Generate and atomically publish the two vanilla base main-shop cards."""
    _preflight_main_shop_generation(run)

    first_run, first_item = _generate_one_main_shop_item(run)
    second_run, second_item = _generate_one_main_shop_item(first_run)

    published = second_run
    for item in (first_item, second_item):
        if isinstance(item, GeneratedShopJokerItem):
            published = insert_generated_shop_joker_item(published, item)
        elif isinstance(item, GeneratedShopConsumableItem):
            published = insert_generated_shop_consumable_item(published, item)
        else:  # defensive boundary for future item kinds
            raise HeadlessTransitionError("unsupported generated main-shop item")

    return GeneratedMainShop(
        run=published,
        items=(first_item, second_item),
    )
