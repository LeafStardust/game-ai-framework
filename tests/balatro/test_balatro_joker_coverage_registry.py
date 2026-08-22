from types import SimpleNamespace

from games.balatro.bonds import evaluate_cash_bond, evaluate_flush_bond, evaluate_tarot_bond
from games.balatro.bonds.catalogue_batch_two import evaluate_straight_bond
from games.balatro.bonds.held_cards import evaluate_held_cards_bond
from games.balatro.bonds.joker_coverage import BOND_WIRED, disposition
from games.balatro.bonds.model import BondRank


def state(*jokers):
    return SimpleNamespace(jokers=list(jokers), owned_deck=[], hand_levels={}, vouchers=[], hand_size=8, money=0)


def sources(dev):
    return {p.source for p in dev.contributions}


def test_superposition_is_low_authority_straight_and_tarot_support():
    straight = evaluate_straight_bond(state("Superposition"))
    tarot = evaluate_tarot_bond(state("Superposition"))
    assert straight.contribution == 2.0
    assert tarot.contribution == 2.0
    assert straight.rank == BondRank.R0
    assert tarot.rank == BondRank.R0


def test_blackboard_is_held_state_support_not_baron_equivalent():
    dev = evaluate_held_cards_bond(state("Blackboard"))
    assert dev.contribution == 4.0
    assert dev.rank == BondRank.R1
    assert sources(dev) == {"Blackboard"}


def test_cloud9_is_low_authority_cash_support():
    dev = evaluate_cash_bond(state("Cloud 9"))
    assert dev.contribution == 3.0
    assert dev.rank == BondRank.R0
    assert sources(dev) == {"Cloud 9"}


def test_8ball_is_low_authority_tarot_support():
    dev = evaluate_tarot_bond(state("8 Ball"))
    assert dev.contribution == 2.0
    assert dev.rank == BondRank.R0
    assert sources(dev) == {"8 Ball"}


def test_ancient_joker_establishes_flush_payoff_support():
    dev = evaluate_flush_bond(state("Ancient Joker"))
    assert dev.contribution == 4.0
    assert dev.rank == BondRank.R1
    assert sources(dev) == {"Ancient Joker"}


def test_registry_records_deliberately_unwired_jokers():
    assert BOND_WIRED["Superposition"] == ("straight", "tarot")
    assert BOND_WIRED["Cloud 9"] == ("cash",)
    assert BOND_WIRED["8 Ball"] == ("tarot",)
    assert BOND_WIRED["Ancient Joker"] == ("flush",)
    assert disposition("Seance") == "tactical_support"
    assert disposition("Campfire") == "tactical_support"
    assert disposition("Obelisk") == "tactical_support"
    assert disposition("Seltzer") == "tactical_support"
    assert disposition("Seeing Double") == "tactical_support"
    assert disposition("The Idol") == "motif_or_composer"
    assert disposition("Hiker") == "motif_or_composer"
    assert disposition("Perkeo") == "motif_or_composer"
