from __future__ import annotations

from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES


RETIRED_NON_STANDALONE = frozenset(
    {
        "abstract_joker",
        "face_held_economy",
        "face_business_card",
        "faceless_discard_economy",
        "planet_satellite",
        "cash_hoard",
        "cash_growth",
        "cash_cloud_nine",
        "discard_mail_rebate",
        "no_discard_reserve",
    }
)


def test_support_only_leaves_cannot_compete_as_standalone_strategies() -> None:
    for strategy_id in RETIRED_NON_STANDALONE:
        definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES[strategy_id]
        assert definition.entry_evidence_cap == 0.0
        assert definition.required_jokers


def test_retired_support_routes_keep_relationship_metadata() -> None:
    """Retirement blocks competition without erasing semantic tier information."""
    cash_growth = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["cash_growth"]
    reserve = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["no_discard_reserve"]

    assert cash_growth.silver_jokers
    assert reserve.silver_jokers
    assert reserve.bronze_jokers


def test_direct_scaling_leaves_remain_active() -> None:
    for strategy_id in (
        "swashbuckler",
        "flower_pot",
        "red_card",
        "no_discard_green",
        "hiker_training",
        "joker_stencil",
        "cash_bull_bootstraps",
        "raised_fist",
    ):
        definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES[strategy_id]
        assert definition.entry_evidence_cap > 0.0