from __future__ import annotations

from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES


RETIRED_NON_STANDALONE = frozenset(
    {
        "abstract_joker",
        "raised_fist",
        "face_held_economy",
        "face_business_card",
        "faceless_discard_economy",
        "planet_satellite",
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
        assert not definition.gold_jokers
        assert not definition.silver_jokers
        assert not definition.bronze_jokers
        assert not definition.gold_consumables
        assert not definition.silver_consumables
        assert not definition.bronze_consumables
        assert not definition.gold_planets
        assert not definition.silver_planets
        assert not definition.bronze_planets
        assert not definition.gold_vouchers
        assert not definition.silver_vouchers
        assert not definition.bronze_vouchers


def test_direct_scaling_leaves_remain_active() -> None:
    for strategy_id in (
        "swashbuckler",
        "flower_pot",
        "red_card",
        "no_discard_green",
        "hiker_training",
        "joker_stencil",
        "cash_growth",
    ):
        definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES[strategy_id]
        assert definition.entry_evidence_cap > 0.0
