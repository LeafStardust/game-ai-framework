"""Source-ordered normal-shop generation through main cards and Boosters."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from games.balatro.env.shop_booster_generation import (
    GeneratedNormalShopBoosters,
    first_shop_buffoon_center,
    generate_first_normal_shop_boosters,
    generate_weighted_normal_shop_boosters,
)
from games.balatro.env.shop_main_generation import (
    GeneratedMainShop,
    generate_base_main_shop,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


@dataclass(frozen=True)
class GeneratedShopWithoutVoucher:
    """Exact inventory result before normal Voucher publication."""

    run: HeadlessRunState
    main: GeneratedMainShop
    boosters: GeneratedNormalShopBoosters


def generate_normal_shop_without_voucher(
    run: HeadlessRunState,
    *,
    first_shop: bool,
    first_buffoon_variant: int | None = None,
    banned_booster_keys: Collection[str] = (),
) -> GeneratedShopWithoutVoucher:
    """Generate main inventory then both Boosters in vanilla source order.

    Voucher publication is intentionally excluded. On the first shop, vanilla's
    unkeyed Buffoon art-variant result must be supplied exactly. On later shops,
    supplying such a variant is contradictory and rejected.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(first_shop, bool):
        raise TypeError("first_shop must be a boolean")
    if first_shop:
        if first_buffoon_variant is None:
            raise HeadlessTransitionError(
                "first shop requires exact unkeyed Buffoon variant authority"
            )
        # Validate the external authority and bans before any keyed shop RNG.
        first_shop_buffoon_center(
            first_buffoon_variant,
            banned_center_keys=banned_booster_keys,
        )
    elif first_buffoon_variant is not None:
        raise HeadlessTransitionError(
            "later shop cannot carry first-shop Buffoon variant authority"
        )

    main = generate_base_main_shop(run)
    if first_shop:
        boosters = generate_first_normal_shop_boosters(
            main.run,
            first_buffoon_variant=first_buffoon_variant,
            banned_center_keys=banned_booster_keys,
        )
    else:
        boosters = generate_weighted_normal_shop_boosters(
            main.run,
            banned_center_keys=banned_booster_keys,
        )
    if boosters.run.public.shop_vouchers:
        raise HeadlessTransitionError(
            "pre-Voucher shop generation unexpectedly published a Voucher"
        )
    return GeneratedShopWithoutVoucher(
        run=boosters.run,
        main=main,
        boosters=boosters,
    )
