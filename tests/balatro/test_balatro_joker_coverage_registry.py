from types import SimpleNamespace

from games.balatro.bonds.catalogue_batch_two import evaluate_straight_bond
from games.balatro.bonds.catalogue_batch_four import evaluate_tarot_bond
from games.balatro.bonds.held_cards import evaluate_held_cards_bond
from games.balatro.bonds.joker_coverage import BOND_WIRED, disposition
from games.balatro.bonds.model import BondRank


def state(*jokers):
    return SimpleNamespace(jokers=list(jokers), owned_deck=[], hand_levels={}, vouchers=[], hand_size=8)


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


def test_registry_records_deliberately_unwired_jokers():
    assert BOND_WIRED["Superposition"] == ("straight", "tarot")
    assert disposition("Seance") == "tactical_support"
    assert disposition("Campfire") == "tactical_support"
    assert disposition("Obelisk") == "tactical_support"
    assert disposition("The Idol") == "motif_or_composer"
    assert disposition("Hiker") == "motif_or_composer"
