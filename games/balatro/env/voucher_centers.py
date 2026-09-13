"""Pinned vanilla Voucher identity order independent of mechanics support."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VanillaVoucherCenter:
    key: str
    order: int
    base_cost: int
    default_unlocked: bool
    requires: tuple[str, ...] = ()


_BASE_UPGRADE_PAIRS = (
    ("v_overstock_norm", "v_overstock_plus"),
    ("v_clearance_sale", "v_liquidation"),
    ("v_hone", "v_glow_up"),
    ("v_reroll_surplus", "v_reroll_glut"),
    ("v_crystal_ball", "v_omen_globe"),
    ("v_telescope", "v_observatory"),
    ("v_grabber", "v_nacho_tong"),
    ("v_wasteful", "v_recyclomancy"),
    ("v_tarot_merchant", "v_tarot_tycoon"),
    ("v_planet_merchant", "v_planet_tycoon"),
    ("v_seed_money", "v_money_tree"),
    ("v_blank", "v_antimatter"),
    ("v_magic_trick", "v_illusion"),
    ("v_hieroglyph", "v_petroglyph"),
    ("v_directors_cut", "v_retcon"),
    ("v_paint_brush", "v_palette"),
)

VANILLA_VOUCHER_CENTERS: tuple[VanillaVoucherCenter, ...] = tuple(
    center
    for pair_index, (base, upgrade) in enumerate(_BASE_UPGRADE_PAIRS)
    for center in (
        VanillaVoucherCenter(base, pair_index * 2 + 1, 10, True),
        VanillaVoucherCenter(
            upgrade,
            pair_index * 2 + 2,
            10,
            False,
            (base,),
        ),
    )
)
VANILLA_VOUCHER_CENTER_KEYS = tuple(
    center.key for center in VANILLA_VOUCHER_CENTERS
)


def _validate_catalogue() -> None:
    if len(VANILLA_VOUCHER_CENTERS) != 32:
        raise RuntimeError("vanilla Voucher catalogue must contain 32 centers")
    if len(VANILLA_VOUCHER_CENTER_KEYS) != len(set(VANILLA_VOUCHER_CENTER_KEYS)):
        raise RuntimeError("vanilla Voucher catalogue contains duplicate keys")
    if tuple(center.order for center in VANILLA_VOUCHER_CENTERS) != tuple(
        range(1, 33)
    ):
        raise RuntimeError("vanilla Voucher catalogue order must be exactly 1..32")
    if any(
        center.base_cost != 10
        or center.default_unlocked != (center.order % 2 == 1)
        or len(center.requires) != (0 if center.order % 2 == 1 else 1)
        for center in VANILLA_VOUCHER_CENTERS
    ):
        raise RuntimeError("vanilla Voucher catalogue metadata is inconsistent")


_validate_catalogue()
