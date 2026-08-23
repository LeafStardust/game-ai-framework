from types import SimpleNamespace

from games.balatro.bonds.evaluation import EVALUATORS
from games.balatro.bonds.model import BondRank
from games.balatro.bonds.rank_progression import (
    audit_all_rank_progressions,
    audit_rank_progression,
    canonical_rank_thresholds,
)
from games.balatro.bonds.realization import FROZEN_BOND_IDS


def card(rank="K", enhancement=""):
    return SimpleNamespace(rank=rank, suit="Hearts", enhancement=enhancement, seal="")


def state(*, jokers=(), kings=0):
    return SimpleNamespace(
        jokers=tuple(jokers),
        owned_deck=tuple(card() for _ in range(kings)),
    )


def test_every_frozen_bond_has_one_canonical_progression_table():
    tables = canonical_rank_thresholds()
    assert set(tables) == set(FROZEN_BOND_IDS)


def test_every_canonical_rank_curve_has_distinct_semantic_progression():
    audits = audit_all_rank_progressions()
    failures = {
        bond_id: audit.issues
        for bond_id, audit in audits.items()
        if not audit.healthy
    }
    assert not failures, failures


def test_progression_audit_rejects_compressed_upper_ranks():
    thresholds = {
        BondRank.R1: 4.0,
        BondRank.R2: 8.0,
        BondRank.R3: 12.0,
        BondRank.R4: 19.5,
        BondRank.R5: 20.0,
    }
    audit = audit_rank_progression("compressed", thresholds)
    assert not audit.healthy
    assert any("R4->R5 gap too compressed" in issue for issue in audit.issues)


def test_kings_bond_traverses_all_five_ranks_as_engine_develops():
    evaluator = EVALUATORS["kings"]

    stages = (
        state(jokers=("baronjoker",), kings=0),
        state(jokers=("baronjoker",), kings=6),
        state(jokers=("baronjoker",), kings=24),
        state(jokers=("baronjoker", "triboulet"), kings=18),
        state(jokers=("baronjoker", "triboulet"), kings=40),
    )

    ranks = tuple(evaluator(candidate).rank for candidate in stages)
    assert ranks == (
        BondRank.R1,
        BondRank.R2,
        BondRank.R3,
        BondRank.R4,
        BondRank.R5,
    )


def test_baron_alone_is_recognition_not_established_commitment():
    development = EVALUATORS["kings"](state(jokers=("baronjoker",), kings=0))
    assert development.rank == BondRank.R1
    assert development.next_rank_threshold is not None
    assert development.contribution < development.next_rank_threshold
