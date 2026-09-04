"""Pinned vanilla Joker center order/rarity metadata for exact shop RNG.

This simulator-private catalogue is copied from Balatro ``P_CENTERS`` at
``GladdonT/balatro-source-code@895ab3a25bc6f513fa80885eb59951bf8e76bc55``.
Only center key/global order/rarity are frozen here. Dynamic eligibility remains
owned by the authoritative observed Joker-generation state.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VanillaJokerCenter:
    key: str
    order: int
    rarity: int


# Source order is mechanically significant: vanilla builds each rarity pool by
# filtering this global Joker center order, leaving ineligible entries in-place
# as UNAVAILABLE rather than compacting the pool.
_ORDERED_KEY_RARITY = """
j_joker:1 j_greedy_joker:1 j_lusty_joker:1 j_wrathful_joker:1 j_gluttenous_joker:1 j_jolly:1 j_zany:1 j_mad:1 j_crazy:1 j_droll:1 j_sly:1 j_wily:1 j_clever:1 j_devious:1 j_crafty:1 j_half:1 j_stencil:2 j_four_fingers:2 j_mime:2 j_credit_card:1 j_ceremonial:2 j_banner:1 j_mystic_summit:1 j_marble:2 j_loyalty_card:2 j_8_ball:1 j_misprint:1 j_dusk:2 j_raised_fist:1 j_chaos:1 j_fibonacci:2 j_steel_joker:2 j_scary_face:1 j_abstract:1 j_delayed_grat:1 j_hack:2 j_pareidolia:2 j_gros_michel:1 j_even_steven:1 j_odd_todd:1 j_scholar:1 j_business:1 j_supernova:1 j_ride_the_bus:1 j_space:2 j_egg:1 j_burglar:2 j_blackboard:2 j_runner:1 j_ice_cream:1 j_dna:3 j_splash:1 j_blue_joker:1 j_sixth_sense:2 j_constellation:2 j_hiker:2 j_faceless:1 j_green_joker:1 j_superposition:1 j_todo_list:1 j_cavendish:1 j_card_sharp:2 j_red_card:1 j_madness:2 j_square:1 j_seance:2 j_riff_raff:1 j_vampire:2 j_shortcut:2 j_hologram:2 j_vagabond:3 j_baron:3 j_cloud_9:2 j_rocket:2 j_obelisk:3 j_midas_mask:2 j_luchador:2 j_photograph:1 j_gift:2 j_turtle_bean:2 j_erosion:2 j_reserved_parking:1 j_mail:1 j_to_the_moon:2 j_hallucination:1 j_fortune_teller:1 j_juggler:1 j_drunkard:1 j_stone:2 j_golden:1 j_lucky_cat:2 j_baseball:3 j_bull:2 j_diet_cola:2 j_trading:2 j_flash:2 j_popcorn:1 j_trousers:2 j_ancient:3 j_ramen:2 j_walkie_talkie:1 j_selzer:2 j_castle:2 j_smiley:1 j_campfire:3 j_ticket:1 j_mr_bones:2 j_acrobat:2 j_sock_and_buskin:2 j_swashbuckler:1 j_troubadour:2 j_certificate:2 j_smeared:2 j_throwback:2 j_hanging_chad:1 j_rough_gem:2 j_bloodstone:2 j_arrowhead:2 j_onyx_agate:2 j_glass:2 j_ring_master:2 j_flower_pot:2 j_blueprint:3 j_wee:3 j_merry_andy:2 j_oops:2 j_idol:2 j_seeing_double:2 j_matador:2 j_hit_the_road:3 j_duo:3 j_trio:3 j_family:3 j_order:3 j_tribe:3 j_stuntman:3 j_invisible:3 j_brainstorm:3 j_satellite:2 j_shoot_the_moon:1 j_drivers_license:3 j_cartomancer:2 j_astronomer:2 j_burnt:3 j_bootstraps:2 j_caino:4 j_triboulet:4 j_yorick:4 j_chicot:4 j_perkeo:4
""".split()


VANILLA_JOKER_CENTERS: tuple[VanillaJokerCenter, ...] = tuple(
    VanillaJokerCenter(key, order, int(rarity))
    for order, token in enumerate(_ORDERED_KEY_RARITY, start=1)
    for key, rarity in (token.rsplit(":", 1),)
)

_RARITY_LABEL_TO_ID = {
    "Common": 1,
    "Uncommon": 2,
    "Rare": 3,
    "Legendary": 4,
}


def joker_rarity_id(rarity: str | int) -> int:
    if type(rarity) is int:
        rarity_id = rarity
    elif isinstance(rarity, str):
        try:
            rarity_id = _RARITY_LABEL_TO_ID[rarity]
        except KeyError as exc:
            raise ValueError(f"unsupported Joker rarity: {rarity!r}") from exc
    else:
        raise TypeError("Joker rarity must be an exact integer or canonical label")

    if rarity_id not in (1, 2, 3, 4):
        raise ValueError(f"unsupported Joker rarity: {rarity!r}")
    return rarity_id


def vanilla_joker_pool(rarity: str | int) -> tuple[str, ...]:
    """Return exact vanilla center-key order for one rarity pool."""
    rarity_id = joker_rarity_id(rarity)
    return tuple(
        center.key
        for center in VANILLA_JOKER_CENTERS
        if center.rarity == rarity_id
    )


def _validate_catalogue() -> None:
    if len(VANILLA_JOKER_CENTERS) != 150:
        raise RuntimeError("vanilla Joker catalogue must contain exactly 150 centers")
    keys = [center.key for center in VANILLA_JOKER_CENTERS]
    if len(keys) != len(set(keys)):
        raise RuntimeError("vanilla Joker catalogue contains duplicate center keys")
    if [center.order for center in VANILLA_JOKER_CENTERS] != list(range(1, 151)):
        raise RuntimeError("vanilla Joker catalogue orders must be exactly 1..150")
    if any(center.rarity not in (1, 2, 3, 4) for center in VANILLA_JOKER_CENTERS):
        raise RuntimeError("vanilla Joker catalogue contains an invalid rarity")


_validate_catalogue()
