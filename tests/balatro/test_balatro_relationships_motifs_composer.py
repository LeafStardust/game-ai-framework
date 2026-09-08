from types import SimpleNamespace

from games.balatro.bonds.composer import compose_build
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.motifs import MotifState, evaluate_baron_mime_steel
from games.balatro.bonds.relationships import BondRelationship, relationship_between


def dev(bond_id, rank=BondRank.R3, realization=BondRealization.ACTIVE):
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=10.0,
        rank=rank,
        next_rank_threshold=None,
        contributions=(),
        realization=realization,
    )


def card(rank="", enhancement=""):
    return SimpleNamespace(rank=rank, enhancement=enhancement)


def test_sparse_relationships_default_neutral_and_known_edges():
    assert relationship_between("held_cards", "steel") == BondRelationship.SYNERGY
    assert relationship_between("face_cards", "no_face_cards") == BondRelationship.CONFLICT
    assert relationship_between("pair", "cash") == BondRelationship.NEUTRAL


def test_baron_mime_steel_requires_specific_components_not_generic_held_cards():
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Blackboard"), SimpleNamespace(name="Mime")],
        owned_deck=[card("K", "Steel") for _ in range(4)],
    )
    result = evaluate_baron_mime_steel(
        state,
        [dev("held_cards"), dev("held_retrigger"), dev("steel"), dev("kings")],
    )
    assert result.state == MotifState.POTENTIAL
    assert "BARON" in result.missing_components


def test_baron_mime_steel_becomes_active_when_package_and_bonds_realize():
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Baron"), SimpleNamespace(name="Mime")],
        owned_deck=[card("K", "Steel") for _ in range(5)],
    )
    result = evaluate_baron_mime_steel(
        state,
        [dev("held_cards"), dev("held_retrigger"), dev("steel"), dev("kings")],
    )
    assert result.state == MotifState.ACTIVE


def test_baron_mime_steel_mature_requires_r4_bonds():
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Baron"), SimpleNamespace(name="Mime")],
        owned_deck=[card("K", "Steel") for _ in range(5)],
    )
    result = evaluate_baron_mime_steel(
        state,
        [dev("held_cards", BondRank.R4), dev("held_retrigger", BondRank.R4), dev("steel", BondRank.R4), dev("kings", BondRank.R4)],
    )
    assert result.state == MotifState.MATURE


def test_composer_rejects_weaker_conflicting_bond_and_keeps_synergy():
    state = SimpleNamespace(jokers=[], owned_deck=[])
    composition = compose_build(
        state,
        [
            dev("face_cards", BondRank.R4, BondRealization.ACTIVE),
            dev("no_face_cards", BondRank.R2, BondRealization.ACTIVE),
            dev("held_cards", BondRank.R3, BondRealization.ACTIVE),
            dev("steel", BondRank.R3, BondRealization.ACTIVE),
        ],
    )
    assert "face_cards" in composition.bond_ids
    assert "no_face_cards" not in composition.bond_ids
    assert ("held_cards", "steel") in composition.synergies or ("steel", "held_cards") in composition.synergies
    assert composition.coherence_score > 0
