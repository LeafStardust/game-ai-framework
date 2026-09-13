from games.balatro.env.voucher_centers import (
    VANILLA_VOUCHER_CENTERS,
    VANILLA_VOUCHER_CENTER_KEYS,
)


def test_env_voucher_catalogue_pins_all_source_positions_and_dependencies():
    assert len(VANILLA_VOUCHER_CENTERS) == 32
    assert tuple(center.order for center in VANILLA_VOUCHER_CENTERS) == tuple(
        range(1, 33)
    )
    assert VANILLA_VOUCHER_CENTER_KEYS[:4] == (
        "v_overstock_norm",
        "v_overstock_plus",
        "v_clearance_sale",
        "v_liquidation",
    )
    assert VANILLA_VOUCHER_CENTER_KEYS[-2:] == ("v_paint_brush", "v_palette")
    for base, upgrade in zip(
        VANILLA_VOUCHER_CENTERS[::2],
        VANILLA_VOUCHER_CENTERS[1::2],
        strict=True,
    ):
        assert base.default_unlocked is True
        assert base.requires == ()
        assert upgrade.default_unlocked is False
        assert upgrade.requires == (base.key,)
        assert (base.base_cost, upgrade.base_cost) == (10, 10)
