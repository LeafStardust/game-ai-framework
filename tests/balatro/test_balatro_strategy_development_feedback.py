from __future__ import annotations

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.strategy_development import reinforce_developments
from games.balatro.bonds.strategy_semantics import SemanticLink, StrategyCandidate, StrategyCommitment


def _dev(bond_id: str, rank: BondRank, value: float, next_threshold: float | None) -> BondDevelopment:
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=value,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=(BondContribution("Concrete Joker", value),),
        realization=BondRealization.PARTIAL,
    )


def _candidate(commitment: StrategyCommitment, *links: SemanticLink) -> StrategyCandidate:
    bonds = tuple(sorted({bond for link in links for bond in (link.left_bond, link.right_bond)}))
    sources = tuple(dict.fromkeys(source for link in links for source in (link.left_source, link.right_source)))
    return StrategyCandidate(
        strategy_id="test-engine",
        bond_ids=bonds,
        sources=sources,
        roles=(),
        links=tuple(links),
        motif_ids=(),
        commitment=commitment,
        confidence=0.8,
        strength=20.0,
        prescriptions=(),
    )


def test_pinned_concrete_engine_can_advance_r1_bond_to_r2() -> None:
    dev = _dev("pair", BondRank.R1, 4.0, 8.0)
    candidate = _candidate(
        StrategyCommitment.PINNED,
        SemanticLink("pair", "Jolly Joker", "hand_repetition", "Supernova", "HAND_ENGINE"),
    )

    reinforced = reinforce_developments((dev,), candidate)[0]

    assert reinforced.rank == BondRank.R2
    assert reinforced.contribution == 8.0
    assert reinforced.next_rank_threshold == 13.0
    assert reinforced.contributions[-1].source == "Pinned strategy coherence: test-engine"


def test_strategy_coherence_never_advances_more_than_one_raw_rank() -> None:
    dev = _dev("pair", BondRank.R1, 4.0, 8.0)
    candidate = _candidate(
        StrategyCommitment.DOMINANT,
        SemanticLink("pair", "Jolly Joker", "hand_repetition", "Supernova", "HAND_ENGINE"),
        SemanticLink("pair", "Jolly Joker", "played_retrigger", "Hanging Chad", "RETRIGGER"),
    )

    reinforced = reinforce_developments((dev,), candidate)[0]

    assert reinforced.rank == BondRank.R2
    assert reinforced.rank != BondRank.R3


def test_ambient_feature_link_cannot_reinforce_a_bond() -> None:
    dev = _dev("spades", BondRank.R1, 4.0, 8.0)
    candidate = _candidate(
        StrategyCommitment.PINNED,
        SemanticLink("spades", "feature:suit:spades", "flush", "Droll Joker", "OUTPUT_FEEDS_SCALING"),
    )

    reinforced = reinforce_developments((dev,), candidate)[0]

    assert reinforced == dev


def test_concrete_side_does_not_promote_ambient_other_bond() -> None:
    spades = _dev("spades", BondRank.R1, 4.0, 8.0)
    flush = _dev("flush", BondRank.R1, 4.0, 8.0)
    candidate = _candidate(
        StrategyCommitment.PINNED,
        SemanticLink("spades", "feature:suit:spades", "flush", "Droll Joker", "OUTPUT_FEEDS_SCALING"),
    )

    reinforced = {dev.bond_id: dev for dev in reinforce_developments((spades, flush), candidate)}

    assert reinforced["spades"] == spades
    assert reinforced["flush"] == flush


def test_coherence_cannot_create_r5_capstone() -> None:
    # Full House post-audit thresholds end at R5=22; R4 is 17.
    dev = _dev("full_house", BondRank.R4, 17.0, 22.0)
    candidate = _candidate(
        StrategyCommitment.DOMINANT,
        SemanticLink("full_house", "The Trio", "hand_repetition", "Supernova", "HAND_ENGINE"),
    )

    reinforced = reinforce_developments((dev,), candidate)[0]

    assert reinforced.rank == BondRank.R4
    assert reinforced.contribution == 17.0


def test_forming_strategy_has_no_rank_authority() -> None:
    dev = _dev("pair", BondRank.R1, 4.0, 8.0)
    candidate = _candidate(
        StrategyCommitment.FORMING,
        SemanticLink("pair", "Jolly Joker", "hand_repetition", "Supernova", "HAND_ENGINE"),
    )

    assert reinforce_developments((dev,), candidate) == (dev,)
