"""Exact normal-shop Booster selection, materialization, and publication."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from games.balatro.env.shop_pricing import vanilla_card_cost
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import shop_pricing_vouchers_are_exact
from games.balatro.jokers.astronomer import AstronomerJoker


@dataclass(frozen=True)
class BoosterCenterDefinition:
    center_key: str
    order: int
    family: str
    label: str
    weight: float
    base_cost: int
    pack_size: int
    choices: int


def _family_centers(
    family: str,
    label: str,
    order: int,
    *,
    normal_weight: float,
    jumbo_weight: float,
    mega_weight: float,
    normal_variants: int = 4,
    jumbo_variants: int = 2,
    mega_variants: int = 2,
    normal_size: int = 3,
    large_size: int = 5,
) -> tuple[BoosterCenterDefinition, ...]:
    result: list[BoosterCenterDefinition] = []
    next_order = order
    for size, variants, weight, cost, pack_size, choices, prefix in (
        ("normal", normal_variants, normal_weight, 4, normal_size, 1, ""),
        ("jumbo", jumbo_variants, jumbo_weight, 6, large_size, 1, "Jumbo "),
        ("mega", mega_variants, mega_weight, 8, large_size, 2, "Mega "),
    ):
        for variant in range(1, variants + 1):
            result.append(
                BoosterCenterDefinition(
                    center_key=f"p_{family.lower()}_{size}_{variant}",
                    order=next_order,
                    family=family,
                    label=f"{prefix}{label} Pack",
                    weight=weight,
                    base_cost=cost,
                    pack_size=pack_size,
                    choices=choices,
                )
            )
            next_order += 1
    return tuple(result)


# Pinned vanilla ``G.P_CENTER_POOLS.Booster`` order and immutable center data.
VANILLA_BOOSTER_CENTERS = tuple(
    sorted(
        (
            *_family_centers(
                "Arcana", "Arcana", 1,
                normal_weight=1.0, jumbo_weight=1.0, mega_weight=0.25,
            ),
            *_family_centers(
                "Celestial", "Celestial", 9,
                normal_weight=1.0, jumbo_weight=1.0, mega_weight=0.25,
            ),
            *_family_centers(
                "Standard", "Standard", 17,
                normal_weight=1.0, jumbo_weight=1.0, mega_weight=0.25,
            ),
            *_family_centers(
                "Buffoon", "Buffoon", 25,
                normal_weight=0.6,
                jumbo_weight=0.6,
                mega_weight=0.15,
                normal_variants=2,
                jumbo_variants=1,
                mega_variants=1,
                normal_size=2,
                large_size=4,
            ),
            *_family_centers(
                "Spectral", "Spectral", 29,
                normal_weight=0.3,
                jumbo_weight=0.3,
                mega_weight=0.07,
                normal_variants=2,
                jumbo_variants=1,
                mega_variants=1,
                normal_size=2,
                large_size=4,
            ),
        ),
        key=lambda center: center.order,
    )
)
_BOOSTER_BY_KEY = {center.center_key: center for center in VANILLA_BOOSTER_CENTERS}
if (
    len(VANILLA_BOOSTER_CENTERS) != 32
    or len(_BOOSTER_BY_KEY) != 32
    or tuple(center.order for center in VANILLA_BOOSTER_CENTERS)
    != tuple(range(1, 33))
):
    raise RuntimeError("pinned vanilla Booster catalogue is internally inconsistent")


@dataclass(frozen=True)
class ShopBoosterPoll:
    run: HeadlessRunState
    center: BoosterCenterDefinition


@dataclass(frozen=True)
class GeneratedShopBoosterItem:
    center_key: str
    family: str
    label: str
    base_cost: int
    price: int
    pack_size: int
    choices: int
    booster_position: int
    discovered: bool | None = None

    @property
    def kind(self) -> str:
        return "BOOSTER"

    @property
    def center(self) -> str:
        return self.center_key


@dataclass(frozen=True)
class GeneratedNormalShopBoosters:
    run: HeadlessRunState
    items: tuple[GeneratedShopBoosterItem, GeneratedShopBoosterItem]


def _validate_boundary(run: HeadlessRunState) -> None:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("Booster generation requires an active SHOP")
    if type(state.ante) is not int or state.ante < 1:
        raise HeadlessTransitionError("Booster generation requires a positive exact Ante")
    if run.tags:
        raise HeadlessTransitionError("normal Booster generation does not own active Tags")
    if len(state.shop_boosters) >= 2:
        raise HeadlessTransitionError("normal Booster shop area is already full")
    if state.shop_inflation_observed is not True:
        raise HeadlessTransitionError("shop inflation is not authoritative")
    if state.shop_discount_percent_observed is not True:
        raise HeadlessTransitionError("shop discount percent is not authoritative")
    if not shop_pricing_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "Booster pricing does not match current Voucher ownership"
        )


def _validated_banned_keys(banned_center_keys: Collection[str]) -> frozenset[str]:
    if isinstance(banned_center_keys, (str, bytes)) or not isinstance(
        banned_center_keys, Collection
    ):
        raise HeadlessTransitionError("banned Booster keys must be a collection")
    try:
        keys = frozenset(banned_center_keys)
    except TypeError as exc:
        raise HeadlessTransitionError(
            "banned Booster keys must contain hashable strings"
        ) from exc
    if any(not isinstance(key, str) or key not in _BOOSTER_BY_KEY for key in keys):
        raise HeadlessTransitionError("banned Booster keys are not pinned centers")
    return keys


def poll_weighted_normal_shop_booster(
    run: HeadlessRunState,
    *,
    banned_center_keys: Collection[str] = (),
) -> ShopBoosterPoll:
    """Mirror weighted ``get_pack('shop_pack')`` for a non-forced slot."""
    _validate_boundary(run)
    banned = _validated_banned_keys(banned_center_keys)
    eligible = tuple(
        center for center in VANILLA_BOOSTER_CENTERS
        if center.center_key not in banned
    )
    if not eligible:
        raise HeadlessTransitionError("normal Booster pool has no eligible center")

    total_weight = sum(center.weight for center in eligible)
    next_run = run.copy()
    poll = next_run.rng.random(f"shop_pack{run.public.ante}") * total_weight
    cumulative = 0.0
    for center in eligible:
        cumulative += center.weight
        if cumulative >= poll and cumulative - center.weight <= poll:
            return ShopBoosterPoll(next_run, center)
    raise HeadlessTransitionError("weighted Booster poll did not select a center")


def first_shop_buffoon_center(
    variant: int,
    *,
    banned_center_keys: Collection[str] = (),
) -> BoosterCenterDefinition:
    """Validate the exact result of vanilla's unkeyed first-shop Buffoon roll."""
    banned = _validated_banned_keys(banned_center_keys)
    if "p_buffoon_normal_1" in banned:
        raise HeadlessTransitionError(
            "first-shop Buffoon override is disabled by authoritative bans"
        )
    if type(variant) is not int or variant not in (1, 2):
        raise HeadlessTransitionError(
            "first-shop Buffoon variant requires exact unkeyed RNG authority"
        )
    return _BOOSTER_BY_KEY[f"p_buffoon_normal_{variant}"]


def materialize_normal_shop_booster(
    run: HeadlessRunState,
    center: BoosterCenterDefinition,
    *,
    booster_position: int,
) -> GeneratedShopBoosterItem:
    """Create exact policy-visible Booster metadata and normal-mode price."""
    _validate_boundary(run)
    if not isinstance(center, BoosterCenterDefinition) or (
        _BOOSTER_BY_KEY.get(center.center_key) != center
    ):
        raise HeadlessTransitionError("Booster center definition is not pinned")
    if type(booster_position) is not int or booster_position not in (1, 2):
        raise HeadlessTransitionError("Booster position must be exact slot 1 or 2")

    price = vanilla_card_cost(
        center.base_cost,
        edition=None,
        inflation=run.public.shop_inflation,
        discount_percent=run.public.shop_discount_percent,
    )
    if center.family == "Celestial" and any(
        type(joker) is AstronomerJoker for joker in run.public.jokers
    ):
        price = 0
    return GeneratedShopBoosterItem(
        center_key=center.center_key,
        family=center.family,
        label=center.label,
        base_cost=center.base_cost,
        price=price,
        pack_size=center.pack_size,
        choices=center.choices,
        booster_position=booster_position,
        discovered=run.generated_center_discovered(center.center_key),
    )


def insert_generated_shop_booster(
    run: HeadlessRunState,
    item: GeneratedShopBoosterItem,
) -> HeadlessRunState:
    """Publish one generated Booster in exact source slot order."""
    _validate_boundary(run)
    if not isinstance(item, GeneratedShopBoosterItem):
        raise TypeError("item must be GeneratedShopBoosterItem")
    expected_position = len(run.public.shop_boosters) + 1
    if item.booster_position != expected_position:
        raise HeadlessTransitionError("Booster publication position is out of order")
    next_run = run.copy()
    next_run.public.shop_boosters.append(item)
    return next_run


def generate_weighted_normal_shop_boosters(
    run: HeadlessRunState,
    *,
    banned_center_keys: Collection[str] = (),
) -> GeneratedNormalShopBoosters:
    """Generate two ordinary weighted Booster slots atomically."""
    _validate_boundary(run)
    if run.public.shop_boosters:
        raise HeadlessTransitionError("weighted Booster generation requires empty slots")
    _validated_banned_keys(banned_center_keys)

    next_run = run
    items: list[GeneratedShopBoosterItem] = []
    for position in (1, 2):
        polled = poll_weighted_normal_shop_booster(
            next_run,
            banned_center_keys=banned_center_keys,
        )
        item = materialize_normal_shop_booster(
            polled.run,
            polled.center,
            booster_position=position,
        )
        next_run = insert_generated_shop_booster(polled.run, item)
        items.append(item)
    return GeneratedNormalShopBoosters(next_run, (items[0], items[1]))


def generate_first_normal_shop_boosters(
    run: HeadlessRunState,
    *,
    first_buffoon_variant: int,
    banned_center_keys: Collection[str] = (),
) -> GeneratedNormalShopBoosters:
    """Generate the forced first Buffoon slot and subsequent weighted slot.

    Vanilla chooses the Buffoon art variant through global, unkeyed
    ``math.random(1, 2)``. The deterministic headless state does not own that
    UI-coupled RNG stream, so its exact result is mandatory input; omission or
    invalid authority fails closed before keyed RNG advances.
    """
    _validate_boundary(run)
    if run.public.shop_boosters:
        raise HeadlessTransitionError("first-shop Booster generation requires empty slots")
    first_center = first_shop_buffoon_center(
        first_buffoon_variant,
        banned_center_keys=banned_center_keys,
    )

    first_item = materialize_normal_shop_booster(
        run,
        first_center,
        booster_position=1,
    )
    after_first = insert_generated_shop_booster(run, first_item)
    second_poll = poll_weighted_normal_shop_booster(
        after_first,
        banned_center_keys=banned_center_keys,
    )
    second_item = materialize_normal_shop_booster(
        second_poll.run,
        second_poll.center,
        booster_position=2,
    )
    result = insert_generated_shop_booster(second_poll.run, second_item)
    return GeneratedNormalShopBoosters(result, (first_item, second_item))
