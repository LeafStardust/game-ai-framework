from games.balatro.bonds import evaluation
from games.balatro.bonds.composer import Composition


def test_structural_composition_boundary_exposes_no_strategy_authority(monkeypatch):
    state = object()
    developments = (object(),)
    motif = object()
    composition = Composition(
        bond_ids=("steel", "held_retrigger"),
        motifs=(motif,),
        conflicts=(("steel", "deck_thinning"),),
        synergies=(("steel", "held_retrigger"),),
        coherence_score=0.73,
        motif_distance=(("baron_mime_steel", 1),),
    )

    monkeypatch.setattr(evaluation, "evaluate_all_bonds", lambda value: developments)
    monkeypatch.setattr(evaluation, "compose_build", lambda value, raw: composition)

    raw, structural = evaluation.evaluate_bond_structure(state)

    assert raw == developments
    assert structural == composition
    assert not hasattr(structural, "prescriptions")
    assert not hasattr(structural, "strategy_candidates")
    assert not hasattr(structural, "pinned_strategy_id")
    assert not hasattr(structural, "strategy_plan")
    assert not hasattr(structural, "pivot_resistance")
