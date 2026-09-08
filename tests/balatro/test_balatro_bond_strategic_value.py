from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.strategic_value import (
    BOND_STRENGTH_EXPONENT,
    REALIZATION_FACTORS,
    bond_strength,
    value_bond,
    value_developments,
)


def development(
    points: float,
    *,
    realization: BondRealization = BondRealization.ACTIVE,
    rank: BondRank = BondRank.R2,
    unlocked: bool = True,
    bond_id: str = "pair",
) -> BondDevelopment:
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=unlocked,
        contribution=points,
        rank=rank,
        next_rank_threshold=None,
        contributions=(),
        realization=realization,
    )


def test_bond_strength_is_zero_at_zero_and_monotonic():
    values = [bond_strength(points) for points in (0.0, 1.0, 4.0, 9.0, 16.0)]
    assert values[0] == 0.0
    assert values == sorted(values)
    assert len(set(values)) == len(values)
    assert BOND_STRENGTH_EXPONENT > 1.0


def test_bond_strength_rewards_deeper_development_with_larger_marginal_gain():
    early_gain = bond_strength(6.0) - bond_strength(5.0)
    late_gain = bond_strength(16.0) - bond_strength(15.0)
    assert late_gain > early_gain > 0.0


def test_realization_factor_monotonically_increases_strategic_value():
    values = [
        value_bond(development(12.0, realization=realization)).value
        for realization in (
            BondRealization.DORMANT,
            BondRealization.PARTIAL,
            BondRealization.ACTIVE,
            BondRealization.MATURE,
        )
    ]
    assert values == sorted(values)
    assert values[0] == 0.0
    assert values[-1] > values[-2] > values[1]
    assert list(REALIZATION_FACTORS.values()) == sorted(REALIZATION_FACTORS.values())


def test_rank_does_not_directly_change_value():
    low_rank = value_bond(development(12.0, rank=BondRank.R1)).value
    high_rank = value_bond(development(12.0, rank=BondRank.R5)).value
    assert low_rank == high_rank


def test_locked_bond_has_zero_value_even_with_non_dormant_realization():
    result = value_bond(
        development(
            20.0,
            realization=BondRealization.MATURE,
            rank=BondRank.LOCKED,
            unlocked=False,
        )
    )
    assert result.value == 0.0
    assert result.realization_factor == 0.0


def test_calibration_weight_is_optional_and_multiplicative():
    base = value_bond(development(10.0)).value
    weighted = value_bond(development(10.0), calibration_weight=1.25).value
    assert weighted == base * 1.25


def test_negative_calibration_weight_is_rejected():
    try:
        value_bond(development(10.0), calibration_weight=-0.1)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative calibration weight should fail")


def test_value_developments_preserves_order_and_exposes_explainable_inputs():
    developments = (
        development(8.0, bond_id="pair", realization=BondRealization.PARTIAL),
        development(14.0, bond_id="steel", realization=BondRealization.ACTIVE),
    )
    results = value_developments(developments, calibration_weights={"steel": 1.1})

    assert tuple(result.bond_id for result in results) == ("pair", "steel")
    assert results[0].points == 8.0
    assert results[0].strength == bond_strength(8.0)
    assert results[0].realization == BondRealization.PARTIAL
    assert results[0].development is developments[0]
    assert results[1].calibration_weight == 1.1
    assert results[1].value > results[0].value
