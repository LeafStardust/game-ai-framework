from games.balatro.bonds import evaluation
from games.balatro.bonds.composer import Composition


def test_structural_composition_boundary_strips_strategy_authority(monkeypatch):
    state = object()
    developments = (object(),)
    motif = object()
    strategy_candidate = object()
    strategy_plan = object()
    composition = Composition(
        bond_ids=("steel", "held_retrigger"),
        motifs=(motif,),
        conflicts=(("steel", "deck_thinning"),),
        synergies=(("steel", "held_retrigger"),),
        coherence_score=0.73,
        pivot_resistance=0.42,
        motif_distance=(("baron_mime_steel", 1),),
        prescriptions=("seek_bond:held_cards",),
        strategy_candidates=(strategy_candidate,),
        pinned_strategy_id="baron_mime_steel",
        strategy_plan=strategy_plan,
    )

    monkeypatch.setattr(evaluation, "evaluate_all_bonds", lambda value: developments)
    monkeypatch.setattr(
        evaluation,
        "compose_build",
        lambda value, raw: composition,
    )

    raw, structural = evaluation.evaluate_bond_structure(state)

    assert raw == developments
    assert structural.bond_ids == composition.bond_ids
    assert structural.motifs == composition.motifs
    assert structural.conflicts == composition.conflicts
    assert structural.synergies == composition.synergies
    assert structural.coherence_score == composition.coherence_score
    assert structural.pivot_resistance == composition.pivot_resistance
    assert structural.motif_distance == composition.motif_distance

    assert structural.prescriptions == ()
    assert structural.strategy_candidates == ()
    assert structural.pinned_strategy_id is None
    assert structural.strategy_plan is None
