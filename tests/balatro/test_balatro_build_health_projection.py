from types import SimpleNamespace

from games.balatro.bonds.build_health import BuildHealthState, evaluate_build_health
from games.balatro.bonds.composer import Composition
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
from games.balatro.bonds.score_projection import project_score


def dev(bond_id, rank=BondRank.R4, realization=BondRealization.ACTIVE):
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=20.0,
        rank=rank,
        next_rank_threshold=None,
        contributions=(),
        realization=realization,
    )


def comp(*bond_ids, coherence=100.0, motifs=()):
    return Composition(
        bond_ids=tuple(bond_ids),
        motifs=tuple(motifs),
        conflicts=(),
        synergies=(),
        coherence_score=coherence,
        motif_distance=(),
    )


def test_projection_uses_candidate_scores_not_bond_rank():
    state = SimpleNamespace(blind_requirement=1000, current_score=100, hands_remaining=3)
    projection = project_score(state, candidate_hand_scores=[200, 300, 400])
    assert projection.expected_hand_score == 300
    assert projection.expected_total == 1000
    assert projection.expected_margin == 0


def test_high_coherence_cannot_rescue_unclearable_projection():
    state = SimpleNamespace(blind_requirement=1000, current_score=0, hands_remaining=2, money=100, ante=2)
    projection = project_score(state, candidate_hand_scores=[100, 150, 200])
    developments = [dev("held_cards", BondRank.R5, BondRealization.MATURE)]
    health = evaluate_build_health(state, developments=developments, composition=comp("held_cards", coherence=999.0), projection=projection)
    assert health.state == BuildHealthState.COLLAPSING
    assert "ceiling_projection_cannot_clear" in health.reasons


def test_mature_motif_can_stabilize_already_clearing_build():
    motif = MotifEvaluation(
        motif_id="example",
        state=MotifState.MATURE,
        relevant_bonds=("held_cards",),
        present_components=("A",),
        missing_components=(),
        prescriptions=(),
    )
    state = SimpleNamespace(blind_requirement=1000, current_score=0, hands_remaining=3, money=25, ante=5)
    projection = project_score(state, candidate_hand_scores=[350, 400, 450], clear_probability=0.75)
    developments = [dev("held_cards", BondRank.R4, BondRealization.MATURE)]
    health = evaluate_build_health(state, developments=developments, composition=comp("held_cards", motifs=(motif,)), projection=projection)
    assert projection.expected_clear
    assert health.state in (BuildHealthState.STRONG, BuildHealthState.DOMINANT)


def test_low_realization_downgrades_structurally_coherent_build():
    state = SimpleNamespace(blind_requirement=1000, current_score=0, hands_remaining=3, money=25, ante=4)
    projection = project_score(state, candidate_hand_scores=[400, 450, 500], clear_probability=0.8)
    developments = [dev("held_cards", BondRank.R5, BondRealization.PARTIAL), dev("steel", BondRank.R5, BondRealization.PARTIAL), dev("kings", BondRank.R5, BondRealization.PARTIAL)]
    health = evaluate_build_health(state, developments=developments, composition=comp("held_cards", "steel", "kings", coherence=200.0), projection=projection)
    assert health.state in (BuildHealthState.STABLE, BuildHealthState.FRAGILE)
    assert "selected_bonds_weakly_realized" in health.reasons
