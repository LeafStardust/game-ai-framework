from games.balatro.bonds.mechanical_roles import enrich_contribution
from games.balatro.bonds.model import BondContribution, MechanicalRole


def test_baron_role_distinguishes_held_rank_payoff():
    c = enrich_contribution(BondContribution("Baron", 6.0))
    assert MechanicalRole.HELD_RANK_PAYOFF in c.roles
    assert "KINGS" in c.targets
    assert "CARD_HELD_IN_HAND" in c.conditions


def test_mime_role_is_held_retrigger_not_held_payoff():
    c = enrich_contribution(BondContribution("Mime", 6.0))
    assert c.roles == (MechanicalRole.HELD_RETRIGGER,)
    assert "HELD_CARD_EFFECTS" in c.targets


def test_blackboard_role_is_distinct_from_baron():
    c = enrich_contribution(BondContribution("Blackboard", 4.0))
    assert c.roles == (MechanicalRole.HELD_STATE_PAYOFF,)
    assert "ALL_REMAINING_HELD_CARDS_SPADES_OR_CLUBS" in c.conditions


def test_vampire_and_driver_license_encode_opposed_enhancement_use():
    vampire = enrich_contribution(BondContribution("Vampire", 7.0))
    driver = enrich_contribution(BondContribution("Driver's License", 7.0))
    assert MechanicalRole.ENHANCEMENT_PAYOFF in vampire.roles
    assert "CONSUMES_ENHANCEMENTS" in vampire.conditions
    assert MechanicalRole.ENHANCEMENT_PAYOFF in driver.roles
    assert "PRESERVE_ENHANCEMENTS" in driver.conditions


def test_unknown_sources_remain_backward_compatible():
    original = BondContribution("Some future contributor", 2.0)
    assert enrich_contribution(original) == original
