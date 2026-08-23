from __future__ import annotations

from dataclasses import dataclass

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization, MechanicalRole
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
from games.balatro.bonds.strategy_semantics import StrategyCommitment, form_strategy_candidates, pinned_strategy


@dataclass(frozen=True)
class _Case:
    rank: BondRank
    realization: BondRealization
    value: float


def _dev(bond_id: str, source: str, role: MechanicalRole, case: _Case) -> BondDevelopment:
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=case.value,
        rank=case.rank,
        next_rank_threshold=None,
        contributions=(BondContribution(source, case.value, roles=(role,), targets=("KING",)),),
        target="KING",
        realization=case.realization,
    )


def _baron_mime(case: _Case, *, motif_state: MotifState = MotifState.POTENTIAL):
    devs = (
        _dev("kings", "Baron", MechanicalRole.HELD_RANK_PAYOFF, case),
        _dev("held_retrigger", "Mime", MechanicalRole.HELD_RETRIGGER, case),
    )
    motif = MotifEvaluation(
        motif_id="baron_mime_steel",
        state=motif_state,
        relevant_bonds=("held_cards", "held_retrigger", "steel", "kings"),
        present_components=("BARON", "MIME"),
        missing_components=("KING_INFRASTRUCTURE", "STEEL_INFRASTRUCTURE"),
        prescriptions=("preserve_held_kings_and_steel",),
    )
    return devs, motif


def test_coherent_low_rank_engine_can_pin_before_bonds_are_established() -> None:
    devs, motif = _baron_mime(_Case(BondRank.R0, BondRealization.PARTIAL, 3.0))
    candidate = pinned_strategy(form_strategy_candidates(devs, (motif,)))

    assert candidate is not None
    assert candidate.strategy_id == "baron_mime_steel"
    assert candidate.commitment == StrategyCommitment.PINNED
    assert all(dev.rank == BondRank.R0 for dev in devs)


def test_strategy_commitment_grows_when_bond_rank_and_realization_mature() -> None:
    low_devs, low_motif = _baron_mime(_Case(BondRank.R1, BondRealization.PARTIAL, 5.0))
    low = pinned_strategy(form_strategy_candidates(low_devs, (low_motif,)))
    assert low is not None
    assert low.commitment == StrategyCommitment.PINNED

    established_devs, _ = _baron_mime(_Case(BondRank.R3, BondRealization.ACTIVE, 14.0))
    established_motif = MotifEvaluation(
        "baron_mime_steel",
        MotifState.ACTIVE,
        ("held_cards", "held_retrigger", "steel", "kings"),
        ("BARON", "MIME", "KING_INFRASTRUCTURE", "STEEL_INFRASTRUCTURE"),
        (),
        ("preserve_held_kings_and_steel",),
    )
    established = pinned_strategy(form_strategy_candidates(established_devs, (established_motif,)))
    assert established is not None
    assert established.commitment >= StrategyCommitment.ESTABLISHED

    dominant_devs, _ = _baron_mime(_Case(BondRank.R5, BondRealization.MATURE, 24.0))
    dominant_motif = MotifEvaluation(
        "baron_mime_steel",
        MotifState.MATURE,
        ("held_cards", "held_retrigger", "steel", "kings"),
        ("BARON", "MIME", "KING_INFRASTRUCTURE", "STEEL_INFRASTRUCTURE"),
        (),
        ("preserve_held_kings_and_steel",),
    )
    dominant = pinned_strategy(form_strategy_candidates(dominant_devs, (dominant_motif,)))
    assert dominant is not None
    assert dominant.commitment == StrategyCommitment.DOMINANT
    assert dominant.strength > established.strength > low.strength


def test_rank_alone_does_not_pin_mechanically_unrelated_bonds() -> None:
    case = _Case(BondRank.R5, BondRealization.MATURE, 25.0)
    unrelated = (
        _dev("kings", "Baron", MechanicalRole.HELD_RANK_PAYOFF, case),
        BondDevelopment(
            bond_id="cash",
            unlocked=True,
            contribution=25.0,
            rank=BondRank.R5,
            next_rank_threshold=None,
            contributions=(BondContribution("Bull", 25.0, roles=(MechanicalRole.ECONOMY_PAYOFF,), targets=("MONEY",)),),
            target="MONEY",
            realization=BondRealization.MATURE,
        ),
    )

    assert pinned_strategy(form_strategy_candidates(unrelated)) is None


def test_pin_does_not_require_high_rank_but_dominance_requires_maturity() -> None:
    partial_devs, motif = _baron_mime(_Case(BondRank.R0, BondRealization.PARTIAL, 3.0))
    partial = pinned_strategy(form_strategy_candidates(partial_devs, (motif,)))
    assert partial is not None
    assert partial.commitment == StrategyCommitment.PINNED

    active_devs, motif = _baron_mime(_Case(BondRank.R5, BondRealization.ACTIVE, 24.0))
    active = pinned_strategy(form_strategy_candidates(active_devs, (motif,)))
    assert active is not None
    assert active.commitment < StrategyCommitment.DOMINANT
