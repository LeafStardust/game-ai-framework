"""Frozen profile authority for deterministic Red/White PPO episodes.

The game seed does not identify a Balatro profile.  Shop pools also depend on
profile unlocks plus run-local bans, flags, used centers, and played hands.
This module freezes those inputs for training instead of borrowing an observed
live profile or treating every pinned center as eligible.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.consumable_centers import (
    VANILLA_PLANET_CENTER_ORDER,
    VANILLA_TAROT_CENTER_ORDER,
)
from games.balatro.env.joker_centers import VANILLA_JOKER_CENTERS
from games.balatro.env.shop_booster_generation import VANILLA_BOOSTER_CENTERS
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


PPO_TRAINING_PROFILE_SCHEMA = "balatro-red-white-pristine-profile-v1"


@dataclass(frozen=True, slots=True)
class PPOTrainingProfileContract:
    schema: str = PPO_TRAINING_PROFILE_SCHEMA
    deck: str = "RED"
    stake: str = "WHITE"
    source_revision: str = "895ab3a25bc6f513fa80885eb59951bf8e76bc55"
    unlock_policy: str = "PINNED_VANILLA_NEW_PROFILE_DEFAULTS"
    discovery_policy: str = "PINNED_DEFAULTS_NOT_GENERATION_ELIGIBILITY"
    first_shop_buffoon_variant: int = 1


PPO_TRAINING_PROFILE = PPOTrainingProfileContract()


# Exact cost metadata for the 105 Jokers unlocked in a new vanilla profile,
# retained in global P_CENTERS order. Dynamic initial-run gates are applied
# below; locked positions remain absent from the observed-style eligible pools.
_DEFAULT_UNLOCKED_JOKERS = """
j_joker:1:2 j_greedy_joker:1:5 j_lusty_joker:1:5 j_wrathful_joker:1:5 j_gluttenous_joker:1:5 j_jolly:1:3 j_zany:1:4 j_mad:1:4 j_crazy:1:4 j_droll:1:4 j_sly:1:3 j_wily:1:4 j_clever:1:4 j_devious:1:4 j_crafty:1:4 j_half:1:5
j_stencil:2:8 j_four_fingers:2:7 j_mime:2:5 j_credit_card:1:1 j_ceremonial:2:6 j_banner:1:5 j_mystic_summit:1:5 j_marble:2:6 j_loyalty_card:2:5 j_8_ball:1:5 j_misprint:1:4 j_dusk:2:5 j_raised_fist:1:5 j_chaos:1:4 j_fibonacci:2:8 j_steel_joker:2:7 j_scary_face:1:4 j_abstract:1:4 j_delayed_grat:1:4 j_hack:2:6 j_pareidolia:2:5 j_gros_michel:1:5 j_even_steven:1:4 j_odd_todd:1:4 j_scholar:1:4 j_business:1:4 j_supernova:1:5 j_ride_the_bus:1:6 j_space:2:5 j_egg:1:4 j_burglar:2:6 j_blackboard:2:6 j_runner:1:5 j_ice_cream:1:5 j_dna:3:8 j_splash:1:3 j_blue_joker:1:5 j_sixth_sense:2:6 j_constellation:2:6 j_hiker:2:5 j_faceless:1:4 j_green_joker:1:4 j_superposition:1:4 j_todo_list:1:4 j_cavendish:1:4 j_card_sharp:2:6 j_red_card:1:5 j_madness:2:7 j_square:1:4 j_seance:2:6 j_riff_raff:1:6 j_vampire:2:7 j_shortcut:2:7 j_hologram:2:7 j_vagabond:3:8 j_baron:3:8 j_cloud_9:2:7 j_rocket:2:6 j_obelisk:3:8 j_midas_mask:2:7 j_luchador:2:5 j_photograph:1:5 j_gift:2:6 j_turtle_bean:2:6 j_erosion:2:6 j_reserved_parking:1:6 j_mail:1:4 j_to_the_moon:2:5 j_hallucination:1:4 j_fortune_teller:1:6 j_juggler:1:4 j_drunkard:1:4 j_stone:2:6 j_golden:1:6 j_lucky_cat:2:6 j_baseball:3:8 j_bull:2:6 j_diet_cola:2:6 j_trading:2:6 j_flash:2:5 j_popcorn:1:5 j_trousers:2:6 j_ancient:3:8 j_ramen:2:6 j_walkie_talkie:1:4 j_selzer:2:6 j_castle:2:6 j_smiley:1:4 j_campfire:3:9
""".split()

_INITIAL_INELIGIBLE_UNLOCKED_JOKERS = frozenset(
    {
        "j_steel_joker",  # no Steel card exists in the pristine Red Deck
        "j_cavendish",  # requires the gros_michel_extinct pool flag
        "j_stone",  # no Stone card exists
        "j_lucky_cat",  # no Lucky card exists
    }
)

_BASE_VOUCHERS = (
    "v_overstock_norm", "v_clearance_sale", "v_hone", "v_reroll_surplus",
    "v_crystal_ball", "v_telescope", "v_grabber", "v_wasteful",
    "v_tarot_merchant", "v_planet_merchant", "v_seed_money", "v_blank",
    "v_magic_trick", "v_hieroglyph", "v_directors_cut", "v_paint_brush",
)
_UPGRADE_VOUCHERS = (
    "v_overstock_plus", "v_liquidation", "v_glow_up", "v_reroll_glut",
    "v_omen_globe", "v_observatory", "v_nacho_tong", "v_recyclomancy",
    "v_tarot_tycoon", "v_planet_tycoon", "v_money_tree", "v_antimatter",
    "v_illusion", "v_petroglyph", "v_retcon", "v_palette",
)

_PROFILE_SHOP_CENTER_KEYS = frozenset(
    tuple(center.key for center in VANILLA_JOKER_CENTERS)
    + VANILLA_TAROT_CENTER_ORDER
    + VANILLA_PLANET_CENTER_ORDER
    + tuple(
        key
        for pair in zip(_BASE_VOUCHERS, _UPGRADE_VOUCHERS, strict=True)
        for key in pair
    )
    + tuple(center.center_key for center in VANILLA_BOOSTER_CENTERS)
)


def pristine_profile_discovery(center_key: str) -> bool:
    """Return pinned new-profile discovery without affecting eligibility.

    Vanilla's base Joker starts discovered. Every other generated shop center
    starts undiscovered, while shop construction still bypasses discovery for
    visible identity. Unknown keys fail closed instead of inheriting a default.
    """
    if (
        not isinstance(center_key, str)
        or center_key not in _PROFILE_SHOP_CENTER_KEYS
    ):
        raise HeadlessTransitionError("center is outside the PPO training profile")
    return center_key == "j_joker"


def _joker_pools() -> dict[str, list[dict]]:
    metadata: dict[str, tuple[int, int]] = {}
    for token in _DEFAULT_UNLOCKED_JOKERS:
        key, rarity, cost = token.split(":")
        metadata[key] = (int(rarity), int(cost))
    source_keys = tuple(center.key for center in VANILLA_JOKER_CENTERS[:105])
    if tuple(metadata) != source_keys:
        raise RuntimeError("PPO default Joker metadata drifted from pinned source order")

    pools = {str(rarity): [] for rarity in (1, 2, 3, 4)}
    for key, (rarity, cost) in metadata.items():
        if key in _INITIAL_INELIGIBLE_UNLOCKED_JOKERS:
            continue
        pools[str(rarity)].append(
            {
                "rarity": rarity,
                "key": key,
                "cost": cost,
                "unlocked": True,
                "no_pool_flag": "gros_michel_extinct" if key == "j_gros_michel" else None,
                "yes_pool_flag": None,
            }
        )
    return pools


def _consumable_pools() -> dict[str, list[dict]]:
    def record(card_type: str, key: str) -> dict:
        return {
            "type": card_type,
            "key": key,
            "cost": 3,
            "unlocked": True,
            "no_pool_flag": None,
            "yes_pool_flag": None,
            "softlock": False,
            "hand_type": None,
        }

    # The three secret hands are unplayed at a pristine boundary, so their
    # Planets remain softlocked and absent from the eligible catalogue.
    return {
        "Tarot": [record("Tarot", key) for key in VANILLA_TAROT_CENTER_ORDER],
        "Planet": [record("Planet", key) for key in VANILLA_PLANET_CENTER_ORDER[:9]],
    }


def _voucher_pool() -> list[dict]:
    result: list[dict] = []
    for base, upgrade in zip(_BASE_VOUCHERS, _UPGRADE_VOUCHERS, strict=True):
        result.append(
            {"key": base, "cost": 10, "unlocked": True, "requires": [],
             "no_pool_flag": None, "yes_pool_flag": None, "eligible": True}
        )
        result.append(
            {"key": upgrade, "cost": 10, "unlocked": False, "requires": [base],
             "no_pool_flag": None, "yes_pool_flag": None, "eligible": False}
        )
    return result


def initialize_pristine_ppo_generation_authority(
    run: HeadlessRunState,
) -> HeadlessRunState:
    """Install exact new-profile pools on a pristine Red/White reset."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if (
        state.deck_name != "RED"
        or state.stake_name != "WHITE"
        or state.phase != "BLIND_SELECT"
        or state.ante != 1
        or state.round != 0
        or state.money != 4
        or state.jokers
        or state.consumables
        or state.vouchers
        or run.tags
    ):
        raise HeadlessTransitionError(
            "PPO training profile authority requires the pristine Red/White reset"
        )
    if any(
        (
            state.joker_generation_pool_observed,
            state.joker_generation_pools,
            state.consumable_generation_pool_observed,
            state.consumable_generation_pools,
            state.voucher_generation_pool_observed,
            state.voucher_generation_pool,
        )
    ):
        raise HeadlessTransitionError("PPO generation authority is already initialized")
    if state.tarot_rate != 4.0 or state.planet_rate != 4.0:
        raise HeadlessTransitionError("pristine shop type rates are not exact")
    if state.joker_generation_edition_rate != 1.0:
        raise HeadlessTransitionError("pristine Joker edition rate is not exact")

    next_run = run.copy()
    next_run.public.joker_generation_pool_observed = True
    next_run.public.joker_generation_pools = _joker_pools()
    next_run.public.consumable_generation_pool_observed = True
    next_run.public.consumable_generation_pools = _consumable_pools()
    next_run.public.voucher_generation_pool_observed = True
    next_run.public.voucher_generation_pool = _voucher_pool()
    return next_run
