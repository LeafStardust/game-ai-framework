from types import SimpleNamespace

from games.balatro.live.runtime.strategy_autonomous_runner import (
    StrategyAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.strategy import NEUTRAL, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES


def _joker(name: str):
    return SimpleNamespace(name=name)


def test_conditional_flush_joker_is_not_unconditional_runtime_evidence():
    flush = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["flush"]

    assert flush.relationship_for(_joker("Seeing Double"), kind="JOKER") == NEUTRAL
    assert flush.relationship_for(_joker("Four Fingers"), kind="JOKER") == SILVER


def test_conditional_straight_flush_components_stay_neutral_until_state_rule_exists():
    straight_flush = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["straight_flush"]

    for name in (
        "Arrowhead",
        "Bloodstone",
        "Onyx Agate",
        "Rough Gem",
        "DNA",
    ):
        assert straight_flush.relationship_for(_joker(name), kind="JOKER") == NEUTRAL

    # Shortcut is consistency support, not a standalone Straight-Flush core.
    assert straight_flush.relationship_for(_joker("Shortcut"), kind="JOKER") == SILVER


def test_the_idol_requires_structural_condition_before_advanced_hand_evidence():
    five_kind = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["five_kind"]
    flush_five = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["flush_five"]

    idol = _joker("The Idol")
    assert five_kind.relationship_for(idol, kind="JOKER") == NEUTRAL
    assert flush_five.relationship_for(idol, kind="JOKER") == NEUTRAL


def test_parenthetical_entries_already_omitted_from_static_catalogue_remain_neutral():
    high_card = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["high_card"]
    three_kind = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["three_kind"]

    assert high_card.relationship_for(_joker("Baron"), kind="JOKER") == NEUTRAL
    assert three_kind.relationship_for(_joker("Scholar"), kind="JOKER") == NEUTRAL
    assert three_kind.relationship_for(_joker("Wee Joker"), kind="JOKER") == NEUTRAL


def test_production_runner_uses_guarded_runtime_catalogue():
    assert (
        StrategyAwareLiveMemoryInjectedSingleStepRunner.__init__.__globals__[
            "RUNTIME_UNIVERSAL_BALATRO_STRATEGIES"
        ]
        is RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
    )
