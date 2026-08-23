from __future__ import annotations

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
from games.balatro.bonds.strategy_plan import build_strategy_plan
from games.balatro.bonds.strategy_semantics import SemanticLink, StrategyCandidate, StrategyCommitment


def _dev(bond_id: str, rank: BondRank, value: float, next_threshold: float | None) -> BondDevelopment:
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=value,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=(BondContribution(bond_id, value),),
        realization=BondRealization.PARTIAL,
    )


def _candidate() -> StrategyCandidate:
    return StrategyCandidate(
        strategy_id="baron_mime_steel",
        bond_ids=("held_retrigger", "kings", "steel"),
        sources=("Baron", "Mime"),
        roles=(),
        links=(
            SemanticLink("kings", "Baron", "held_retrigger", "Mime", "RETRIGGER_AMPLIFIES_HELD_PAYOFF"),
        ),
        motif_ids=("baron_mime_steel",),
        commitment=StrategyCommitment.PINNED,
        confidence=0.8,
        strength=20.0,
        prescriptions=("seek_feature:held:retrigger",),
    )


def test_strategy_plan_tracks_next_bond_ranks_and_missing_pieces() -> None:
    plan = build_strategy_plan(
        _candidate(),
        (
            _dev("kings", BondRank.R1, 5.0, 8.0),
            _dev("held_retrigger", BondRank.R2, 9.0, 13.0),
            _dev("steel", BondRank.R0, 2.0, 4.0),
        ),
        (
            MotifEvaluation(
                "baron_mime_steel",
                MotifState.POTENTIAL,
                ("held_cards", "held_retrigger", "steel", "kings"),
                ("BARON", "MIME"),
                ("KING_INFRASTRUCTURE", "STEEL_INFRASTRUCTURE"),
                ("preserve_held_kings_and_steel",),
            ),
        ),
    )

    assert plan is not None
    assert plan.strategy_id == "baron_mime_steel"
    assert plan.missing_features == ("held:retrigger",)
    assert plan.present_components == ("BARON", "MIME")
    assert plan.missing_components == ("KING_INFRASTRUCTURE", "STEEL_INFRASTRUCTURE")
    goals = {goal.bond_id: goal for goal in plan.bond_goals}
    assert goals["kings"].next_rank == BondRank.R2
    assert goals["kings"].points_to_next_rank == 3.0
    assert goals["held_retrigger"].next_rank == BondRank.R3
    assert goals["steel"].next_rank == BondRank.R1
    assert "seek_bond:kings:R2" in plan.prescriptions
    assert "seek_bond:held_retrigger:R3" in plan.prescriptions
    assert "seek_bond:steel:R1" in plan.prescriptions
    assert "seek_component:KING_INFRASTRUCTURE" in plan.prescriptions
    assert "seek_component:STEEL_INFRASTRUCTURE" in plan.prescriptions


def test_strategy_plan_does_not_exist_before_pin() -> None:
    candidate = _candidate()
    candidate = StrategyCandidate(
        strategy_id=candidate.strategy_id,
        bond_ids=candidate.bond_ids,
        sources=candidate.sources,
        roles=candidate.roles,
        links=candidate.links,
        motif_ids=candidate.motif_ids,
        commitment=StrategyCommitment.FORMING,
        confidence=candidate.confidence,
        strength=candidate.strength,
        prescriptions=candidate.prescriptions,
    )
    assert build_strategy_plan(candidate, (_dev("kings", BondRank.R1, 5.0, 8.0),)) is None


def test_strategy_plan_removes_completed_r5_bond_from_development_queue() -> None:
    plan = build_strategy_plan(
        _candidate(),
        (
            _dev("kings", BondRank.R5, 30.0, None),
            _dev("held_retrigger", BondRank.R2, 9.0, 13.0),
            _dev("steel", BondRank.R1, 5.0, 8.0),
        ),
    )
    assert plan is not None
    assert "kings" not in {goal.bond_id for goal in plan.bond_goals}
