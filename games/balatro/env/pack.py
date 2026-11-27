"""Exact fail-closed booster-pack strategic transitions.

Pinned vanilla G.FUNCS.skip_booster first notifies every Joker with the
skipping_booster context, where Red Card is the only gameplay mutation, then
closes the pack and restores G.GAME.PACK_INTERRUPT. This owner requires that
return origin explicitly because public pack phase alone cannot distinguish a
purchased pack from a Tag-opened pack.
"""

from __future__ import annotations

from games.balatro.env.actions import EnvAction
from games.balatro.env.joker_order import JokerOrderError
from games.balatro.env.shop_booster_generation import GeneratedShopBoosterItem
from games.balatro.env.shop_consumable_generation_state import (
    generate_held_tarot,
    require_held_tarot_authority,
)
from games.balatro.env.shop_generation_state import (
    restore_removed_shop_jokers_to_generation_pool,
    suppress_visible_shop_jokers_from_generation_pool,
)
from games.balatro.env.shop_items import (
    GeneratedShopJokerItem,
    materialize_generated_shop_joker_for_acquisition,
)
from games.balatro.env.shop_joker_generation import generate_ordinary_shop_joker_descriptor
from games.balatro.env.shop_pricing import vanilla_card_cost
from games.balatro.env.tag_selection import TagProfileState
from games.balatro.env.voucher_capabilities import shop_pricing_vouchers_are_exact
from games.balatro.jokers.hallucination import HallucinationJoker
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError, ShopTransitionEngine
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.red_card import RedCardJoker
from games.balatro.env.transition import _EXACT_R1_JOKER_ACQUISITION_TYPES


PACK_PHASES = frozenset(
    {"BUFFOON_PACK", "PLANET_PACK", "SPECTRAL_PACK", "STANDARD_PACK", "TAROT_PACK"}
)


def open_paid_buffoon_pack_exact(run: HeadlessRunState, slot: int) -> HeadlessRunState:
    """Open an ordinary paid Buffoon pack with authoritative profile state."""
    state = run.public
    if (
        state.phase != "SHOP" or not state.shop_active or state.hand
        or run.pack_choices or run.pack_return_phase is not None or run.pack_choices_remaining
        or not run.pending_tags_are_exact()
        or not shop_pricing_vouchers_are_exact(state)
        or state.shop_inflation_observed is not True or state.shop_inflation != 0
    ):
        raise HeadlessTransitionError("paid Buffoon opening requires exact shop state")
    if type(slot) is not int or not 0 <= slot < len(state.shop_boosters):
        raise HeadlessTransitionError("paid Buffoon slot is out of range")
    item = state.shop_boosters[slot]
    if (
        type(item) is not GeneratedShopBoosterItem
        or item.center_key not in ("p_buffoon_normal_1", "p_buffoon_normal_2")
        or (item.family, item.base_cost, item.pack_size, item.choices) != ("Buffoon", 4, 2, 1)
    ):
        raise HeadlessTransitionError("only ordinary generated Buffoon packs are owned")
    price = vanilla_card_cost(
        4, edition=None, inflation=0, discount_percent=state.shop_discount_percent,
    )
    discovery = run.generated_center_discovered(item.center_key)
    if (
        type(item.price) is not int or item.price != price
        or type(state.money) is not int or state.money < price
        or type(discovery) is not bool or item.discovered is not discovery
        or run.tag_profile_state is None
    ):
        raise HeadlessTransitionError("paid Buffoon opening requires exact price and discovery")

    hallucinations = [joker for joker in state.jokers if type(joker) is HallucinationJoker]
    if hallucinations:
        require_held_tarot_authority(run)
        if any(
            getattr(joker, "center", None) != "j_hallucination"
            or getattr(joker, "edition", None) is not None
            or type(joker.debuffed) is not bool
            for joker in hallucinations
        ):
            raise HeadlessTransitionError("Buffoon opening requires exact Hallucination state")
    next_run = run.copy()
    next_run.public.money -= price
    next_run.public.shop_boosters.pop(slot)
    next_run.public.phase = "BUFFOON_PACK"
    next_run.public.shop_active = False
    next_run.pack_return_phase = "SHOP"
    next_run.pack_choices_remaining = 1
    next_run.generation_discovery[item.center_key] = True
    next_run.tag_profile_state = TagProfileState(
        next_run.tag_profile_state.discovered_center_keys | {item.center_key}
    )
    reserved_tarots = 0
    available = state.consumable_slots - len(state.consumables) if hallucinations else 0
    for joker in hallucinations:
        if (
            not joker.debuffed
            and reserved_tarots < available
            and next_run.rng.random(f"halu{state.ante}") < 0.5
        ):
            reserved_tarots += 1

    for _ in range(item.pack_size):
        descriptor = generate_ordinary_shop_joker_descriptor(next_run, key_append="buf")
        option = GeneratedShopJokerItem(
            descriptor.center_key, descriptor.rarity, descriptor.base_cost,
            descriptor.edition, vanilla_card_cost(
                descriptor.base_cost, edition=descriptor.edition, inflation=0,
                discount_percent=state.shop_discount_percent,
            ),
            discovered=descriptor.run.generated_center_discovered(descriptor.center_key),
        )
        next_run = suppress_visible_shop_jokers_from_generation_pool(descriptor.run, (option,))
        next_run.pack_choices.append(option)
    for _ in range(reserved_tarots):
        next_run = generate_held_tarot(next_run, key_append="hal")
    return next_run


def validate_skip_pack_exact(run: HeadlessRunState) -> None:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase not in PACK_PHASES:
        raise HeadlessTransitionError("SKIP_PACK requires an exact open-pack phase")
    if run.pack_return_phase not in {"SHOP", "BLIND_SELECT"}:
        raise HeadlessTransitionError(
            "SKIP_PACK requires authoritative SHOP or BLIND_SELECT return phase"
        )
    if not run.pack_choices:
        raise HeadlessTransitionError("SKIP_PACK requires authoritative offered choices")
    if state.hand:
        raise HeadlessTransitionError("SKIP_PACK does not own nonempty hand-to-deck cleanup")
    if state.shop_active:
        raise HeadlessTransitionError("open-pack public state cannot remain an active main shop")


def validate_choose_pack_option_exact(
    run: HeadlessRunState,
    option_index: int,
) -> None:
    """Validate a one-pick Buffoon choice with inventory-only Joker lifecycle."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "BUFFOON_PACK":
        raise HeadlessTransitionError(
            "exact CHOOSE_PACK_OPTION currently supports BUFFOON_PACK only"
        )
    if run.pack_return_phase not in {"SHOP", "BLIND_SELECT"}:
        raise HeadlessTransitionError(
            "CHOOSE_PACK_OPTION requires authoritative pack return phase"
        )
    if run.pack_choices_remaining != 1:
        raise HeadlessTransitionError(
            "CHOOSE_PACK_OPTION currently requires an exact final pack choice"
        )
    if isinstance(option_index, bool) or not isinstance(option_index, int):
        raise HeadlessTransitionError("pack option index must be an exact integer")
    if option_index < 0 or option_index >= len(run.pack_choices):
        raise HeadlessTransitionError("pack option index is out of range")
    if state.hand or state.shop_active:
        raise HeadlessTransitionError("Buffoon choice requires exact isolated pack state")
    if len(state.jokers) >= state.joker_slots:
        raise HeadlessTransitionError("no Joker capacity for Buffoon choice")

    joker = run.pack_choices[option_index]
    if type(joker) is GeneratedShopJokerItem:
        if not ShopTransitionEngine._joker_acquisition_is_exact(run, joker):
            raise HeadlessTransitionError("generated Buffoon Joker acquisition is not exact")
        joker = materialize_generated_shop_joker_for_acquisition(
            joker, castle_suit=run.castle_suit, mail_rebate_rank=run.mail_rebate_rank,
        )
    if type(joker) not in _EXACT_R1_JOKER_ACQUISITION_TYPES:
        raise HeadlessTransitionError(
            "Buffoon Joker acquisition lifecycle is not exactly owned"
        )
    if getattr(joker, "edition", None) is not None:
        raise HeadlessTransitionError("Buffoon Joker editions remain fail-closed")
    if type(joker) is JugglerJoker:
        raise HeadlessTransitionError(
            "resource-mutating Buffoon Joker acquisition remains fail-closed"
        )
    run.require_joker_order_state()


def can_choose_pack_option_exact(run: HeadlessRunState, option_index: int) -> bool:
    try:
        validate_choose_pack_option_exact(run, option_index)
    except (TypeError, HeadlessTransitionError):
        return False
    return True


def choose_pack_option_exact(
    run: HeadlessRunState,
    option_index: int,
) -> HeadlessRunState:
    validate_choose_pack_option_exact(run, option_index)
    next_run = run.copy()
    offered = next_run.pack_choices[option_index]
    joker = offered
    if type(offered) is GeneratedShopJokerItem:
        joker = materialize_generated_shop_joker_for_acquisition(
            offered, castle_suit=run.castle_suit, mail_rebate_rank=run.mail_rebate_rank,
        )
    if next_run.public.joker_generation_pool_observed:
        # Live used_jokers suppression covers every visible Buffoon option while
        # the pack is open. Closing the pack re-admits each unchosen Joker; the
        # acquired Joker remains suppressed by ownership.
        next_run = restore_removed_shop_jokers_to_generation_pool(
            next_run,
            (
                offered
                for index, offered in enumerate(next_run.pack_choices)
                if index != option_index
            ),
        )
    if next_run.joker_order_state is not None:
        try:
            next_run.joker_order_state.acquire(joker, next_run.public.jokers)
        except JokerOrderError as exc:
            raise HeadlessTransitionError(
                "cannot retain exact Joker order after Buffoon choice"
            ) from exc
    next_run.public.jokers.append(joker)
    if type(offered) is GeneratedShopJokerItem:
        next_run.generation_discovery[offered.center_key] = True
        if next_run.tag_profile_state is not None:
            next_run.tag_profile_state = TagProfileState(
                next_run.tag_profile_state.discovered_center_keys | {offered.center_key}
            )
    next_run.public.phase = next_run.pack_return_phase
    next_run.public.shop_active = next_run.pack_return_phase == "SHOP"
    next_run.pack_choices.clear()
    next_run.pack_choices_remaining = 0
    next_run.pack_return_phase = None
    return next_run


def can_skip_pack_exact(run: HeadlessRunState) -> bool:
    try:
        validate_skip_pack_exact(run)
    except (TypeError, HeadlessTransitionError):
        return False
    return True


def skip_pack_exact(run: HeadlessRunState) -> HeadlessRunState:
    validate_skip_pack_exact(run)
    next_run = run.copy()
    if (
        run.public.phase == "BUFFOON_PACK"
        and run.public.joker_generation_pool_observed
        and all(type(option) is GeneratedShopJokerItem for option in run.pack_choices)
    ):
        next_run = restore_removed_shop_jokers_to_generation_pool(next_run, next_run.pack_choices)
    for joker in next_run.public.jokers:
        if type(joker) is RedCardJoker:
            joker.mult += 3
    next_run.public.phase = next_run.pack_return_phase
    next_run.public.shop_active = next_run.pack_return_phase == "SHOP"
    next_run.pack_choices.clear()
    next_run.pack_choices_remaining = 0
    next_run.pack_return_phase = None
    return next_run


class PackTransitionEngine:
    def legal_actions(self, run: HeadlessRunState) -> tuple[EnvAction, ...]:
        actions = [
            EnvAction.from_alias("CHOOSE_PACK_OPTION", {"option_index": index})
            for index in range(len(run.pack_choices))
            if can_choose_pack_option_exact(run, index)
        ]
        if can_skip_pack_exact(run):
            actions.append(EnvAction.from_alias("SKIP_PACK"))
        return tuple(actions)

    def step(self, run: HeadlessRunState, action: EnvAction) -> HeadlessRunState:
        if action not in self.legal_actions(run):
            raise HeadlessTransitionError(f"illegal pack transition: {action.alias}")
        if action.alias == "CHOOSE_PACK_OPTION":
            option_index = action.payload().get("option_index")
            return choose_pack_option_exact(run, option_index)
        if action.alias == "SKIP_PACK":
            return skip_pack_exact(run)
        raise HeadlessTransitionError(f"unimplemented pack transition: {action.alias}")
