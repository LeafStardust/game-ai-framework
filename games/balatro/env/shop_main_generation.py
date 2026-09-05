"""Source-ordered exact generation for ordinary main-shop slots.

Vanilla calls ``create_card_for_shop(G.shop_jokers)`` once per missing slot and
immediately emplaces each result. Emplacement alone does not call ``add_to_deck``
or mutate ``G.GAME.used_jokers``, so later slot pool eligibility is unchanged by
cards merely remaining visible in the shop. The headless boundary can therefore
keep publication atomic while preserving RNG order.
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
    expected_main_shop_slots_for_vouchers,
    shop_generation_vouchers_are_exact,
    shop_pricing_vouchers_are_exact,
)


GeneratedMainShopItem = GeneratedShopJokerItem | GeneratedShopConsumableItem


@dataclass(frozen=True)
class GeneratedMainShop:
    run: HeadlessRunState
    items: tuple[GeneratedMainShopItem, ...]


@dataclass(frozen=True)
class GeneratedMainShopAddition:
    run: HeadlessRunState
    item: GeneratedMainShopItem


def _preflight_main_shop_generation(run: HeadlessRunState) -> None:
    """Validate every state source an ungenerated normal shop may consume."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("main shop generation requires active SHOP")
    if not shop_generation_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "main shop generation does not own current Voucher modifiers"
        )
    if expected_main_shop_slots_for_vouchers(state) is None:
        raise HeadlessTransitionError("main shop slot count is not exact")
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

    # Any slot may become any positive-rate type. Validate all candidate
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


def _insert_generated_main_item(
    run: HeadlessRunState,
    item: GeneratedMainShopItem,
) -> HeadlessRunState:
    if isinstance(item, GeneratedShopJokerItem):
        return insert_generated_shop_joker_item(run, item)
    if isinstance(item, GeneratedShopConsumableItem):
        return insert_generated_shop_consumable_item(run, item)
    raise HeadlessTransitionError("unsupported generated main-shop item")


def generate_base_main_shop(run: HeadlessRunState) -> GeneratedMainShop:
    """Generate and atomically publish every current normal main-shop slot."""
    _preflight_main_shop_generation(run)

    slot_count = expected_main_shop_slots_for_vouchers(run.public)
    if slot_count is None:
        raise HeadlessTransitionError("main shop slot count is not exact")

    generated_run = run
    items: list[GeneratedMainShopItem] = []
    for _ in range(slot_count):
        generated_run, item = _generate_one_main_shop_item(generated_run)
        items.append(item)

    published = generated_run
    for item in items:
        published = _insert_generated_main_item(published, item)

    return GeneratedMainShop(
        run=published,
        items=tuple(items),
    )


def generate_one_base_main_shop_addition(run: HeadlessRunState) -> GeneratedMainShopAddition:
    """Generate one ``change_shop_size(+1)`` replenishment in exact RNG order.

    ``create_card_for_shop`` does not consult already-visible main-shop cards,
    booster cards, or the current Voucher offer when choosing the new card. The
    lower-level generator intentionally requires an otherwise ungenerated shop,
    so this composition creates an isolated generation view, advances exactly one
    card's RNG there, then restores the untouched visible inventories and inserts
    only that generated card. Persistent owned state and generation catalogues are
    retained throughout.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("main shop addition requires active SHOP")

    existing_jokers = list(state.shop_jokers)
    existing_consumables = list(state.shop_consumables)
    existing_boosters = list(state.shop_boosters)
    existing_vouchers = list(state.shop_vouchers)

    generation_view = run.copy()
    generation_view.public.shop_jokers = []
    generation_view.public.shop_consumables = []
    generation_view.public.shop_boosters = []
    generation_view.public.shop_vouchers = []
    _preflight_main_shop_generation(generation_view)

    generated_run, item = _generate_one_main_shop_item(generation_view)
    generated_run.public.shop_jokers = existing_jokers
    generated_run.public.shop_consumables = existing_consumables
    generated_run.public.shop_boosters = existing_boosters
    generated_run.public.shop_vouchers = existing_vouchers
    published = _insert_generated_main_item(generated_run, item)

    return GeneratedMainShopAddition(run=published, item=item)
