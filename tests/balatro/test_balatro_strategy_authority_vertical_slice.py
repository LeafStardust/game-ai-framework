from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import games.balatro.bonds.composer as composer_module
from games.balatro.bonds.model import (
    BondContribution,
    BondDevelopment,
    BondRank,
    BondRealization,
    MechanicalRole,
)
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
from games.balatro.bonds.strategy_plan import build_strategy_plan
from games.balatro.bonds.strategy_semantics import (
    StrategyCandidate,
    StrategyCommitment,
    form_strategy_candidates,
)


def _development(
    bond_id: str = "deck_thinning",
    *,
    rank: BondRank = BondRank.R1,
    source: str = "Erosion",
    roles: tuple[MechanicalRole, ...] = (),
) -> BondDevelopment:
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=5.0,
        rank=rank,
        next_rank_threshold=8.0,
        contributions=(BondContribution(source=source, value=5.0, roles=roles),),
        realization=BondRealization.PARTIAL,
    )


def _candidate(commitment: StrategyCommitment) -> StrategyCandidate:
    return StrategyCandidate(
        strategy_id="semantic:deck_thinning",
        bond_ids=("deck_thinning",),
        sources=("Erosion",),
        roles=(MechanicalRole.DECK_THIN_PAYOFF,),
        links=(),
        motif_ids=("proof_motif",),
        commitment=commitment,
        confidence=0.5,
        strength=5.0,
        prescriptions=(
            "seek_feature:card_removal",
            "preserve_engine_piece",
            "use_engine_piece_now",
        ),
    )


def test_developed_single_mechanical_axis_can_form_without_second_bond():
    candidates = form_strategy_candidates((_development(),))

    candidate = next(c for c in candidates if c.strategy_id == "semantic:deck_thinning")
    assert candidate.commitment == StrategyCommitment.FORMING
    assert candidate.bond_ids == ("deck_thinning",)
    assert candidate.links == ()


def test_support_or_density_only_evidence_cannot_form_singleton_strategy():
    support_only = _development(
        bond_id="ambient_density",
        rank=BondRank.R2,
        source="Synthetic density",
        roles=(MechanicalRole.DENSITY_INFRASTRUCTURE, MechanicalRole.SUPPORT),
    )

    assert form_strategy_candidates((support_only,)) == ()


def test_forming_plan_is_construction_only_while_pinned_unlocks_stronger_prescriptions():
    development = _development()
    motif = MotifEvaluation(
        motif_id="proof_motif",
        state=MotifState.POTENTIAL,
        relevant_bonds=("deck_thinning",),
        present_components=("EROSION",),
        missing_components=("CARD_REMOVAL",),
        prescriptions=(),
    )

    forming = build_strategy_plan(_candidate(StrategyCommitment.FORMING), (development,), (motif,))
    assert forming is not None
    assert forming.commitment == StrategyCommitment.FORMING
    assert "seek_feature:card_removal" in forming.prescriptions
    assert "seek_bond:deck_thinning:R2" in forming.prescriptions
    assert "seek_component:CARD_REMOVAL" in forming.prescriptions
    assert "preserve_engine_piece" not in forming.prescriptions
    assert "use_engine_piece_now" not in forming.prescriptions

    pinned = build_strategy_plan(_candidate(StrategyCommitment.PINNED), (development,), (motif,))
    assert pinned is not None
    assert "preserve_engine_piece" in pinned.prescriptions
    assert "use_engine_piece_now" in pinned.prescriptions


def test_composer_gives_non_motif_forming_candidate_real_plan_without_promotion(monkeypatch):
    development = _development()
    candidate = replace(_candidate(StrategyCommitment.FORMING), motif_ids=())

    monkeypatch.setattr(composer_module, "evaluate_motifs", lambda state, developments: ())
    monkeypatch.setattr(
        composer_module,
        "form_strategy_candidates",
        lambda developments, motifs=(): (candidate,),
    )
    monkeypatch.setattr(
        composer_module,
        "form_behavior_strategy_candidates",
        lambda state, developments, motifs=(): (),
    )

    composition = composer_module.compose_build(
        SimpleNamespace(hand_play_counts={}),
        (development,),
    )

    assert composition.pinned_strategy_id is None
    assert composition.strategy_plan is not None
    assert composition.strategy_plan.commitment == StrategyCommitment.FORMING
    assert "seek_bond:deck_thinning:R2" in composition.strategy_plan.prescriptions
    assert "preserve_engine_piece" not in composition.strategy_plan.prescriptions
