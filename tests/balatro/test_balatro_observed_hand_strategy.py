from types import SimpleNamespace

from games.balatro.bonds.composer import _hand_bond_id, _observed_hand_strategy_candidates
from games.balatro.bonds.model import BondDevelopment, BondRank
from games.balatro.bonds.strategy_semantics import StrategyCommitment


def _development(bond_id: str) -> BondDevelopment:
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=0.0,
        rank=BondRank.R0,
        next_rank_threshold=1.0,
        contributions=(),
    )


def test_observed_two_pair_history_forms_generic_pinned_fallback():
    state = SimpleNamespace(
        hand_play_counts={
            "Two Pair": 22,
            "Pair": 2,
            "Straight": 3,
            "Flush": 3,
            "Full House": 3,
            "Three of a Kind": 3,
            "High Card": 2,
        }
    )

    candidates = _observed_hand_strategy_candidates(
        state,
        (_development("two_pair"), _development("pair")),
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.strategy_id == "observed_hand:two_pair"
    assert candidate.bond_ids == ("two_pair",)
    assert candidate.commitment == StrategyCommitment.PINNED
    assert "seek_bond:two_pair" in candidate.prescriptions


def test_observed_hand_fallback_requires_real_specialization():
    state = SimpleNamespace(
        hand_play_counts={"Pair": 3, "Two Pair": 2, "Straight": 2}
    )

    assert _observed_hand_strategy_candidates(
        state,
        (_development("pair"), _development("two_pair")),
    ) == ()


def test_hand_bond_normalization_is_generic_for_kind_hands():
    assert _hand_bond_id("Three of a Kind") == "three_kind"
    assert _hand_bond_id("Four of a Kind") == "four_kind"
    assert _hand_bond_id("Five of a Kind") == "five_kind"
