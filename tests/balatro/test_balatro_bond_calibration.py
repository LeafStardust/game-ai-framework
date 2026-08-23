from dataclasses import FrozenInstanceError

import pytest

from games.balatro.bonds.calibration import (
    DEFAULT_BOND_CALIBRATION,
    BondCalibration,
    current_bond_calibration,
    use_bond_calibration,
)
from games.balatro.bonds.model import BondRank


def test_default_bond_calibration_matches_previous_composer_constants():
    calibration = DEFAULT_BOND_CALIBRATION
    assert calibration.realization_priority_weight == pytest.approx(0.75)
    assert calibration.synergy_bonus == pytest.approx(1.5)
    assert calibration.conflict_penalty == pytest.approx(2.0)
    assert (
        calibration.motif_potential_value,
        calibration.motif_active_value,
        calibration.motif_mature_value,
    ) == pytest.approx((1.0, 4.0, 7.0))
    assert calibration.pivot_resistance_values() == pytest.approx((0.5, 1.0, 2.5, 4.5, 7.0))


def test_calibration_snapshot_is_immutable():
    with pytest.raises(FrozenInstanceError):
        DEFAULT_BOND_CALIBRATION.synergy_bonus = 9.0


def test_context_override_is_scoped_and_restores_default():
    override = DEFAULT_BOND_CALIBRATION.with_overrides(synergy_bonus=2.25)
    assert current_bond_calibration() is DEFAULT_BOND_CALIBRATION
    with use_bond_calibration(override):
        assert current_bond_calibration() is override
        assert current_bond_calibration().synergy_bonus == pytest.approx(2.25)
    assert current_bond_calibration() is DEFAULT_BOND_CALIBRATION


def test_nested_context_overrides_restore_parent_snapshot():
    outer = DEFAULT_BOND_CALIBRATION.with_overrides(conflict_penalty=3.0)
    inner = DEFAULT_BOND_CALIBRATION.with_overrides(conflict_penalty=1.0)
    with use_bond_calibration(outer):
        assert current_bond_calibration() is outer
        with use_bond_calibration(inner):
            assert current_bond_calibration() is inner
        assert current_bond_calibration() is outer


def test_serialization_round_trip_is_exact():
    configured = DEFAULT_BOND_CALIBRATION.with_overrides(
        realization_priority_weight=0.9,
        synergy_bonus=1.9,
        pivot_resistance_r5=8.0,
    )
    assert BondCalibration.from_mapping(configured.to_dict()) == configured


def test_unknown_or_incompatible_schema_is_rejected():
    with pytest.raises(ValueError, match="unsupported Bond calibration schema"):
        BondCalibration.from_mapping({"schema_version": 999})
    with pytest.raises(ValueError, match="unknown Bond calibration fields"):
        BondCalibration.from_mapping({"mystery": 1.0})


def test_invalid_monotonic_structural_values_are_rejected():
    with pytest.raises(ValueError, match="POTENTIAL <= ACTIVE <= MATURE"):
        BondCalibration(motif_potential_value=5.0, motif_active_value=4.0)
    with pytest.raises(ValueError, match="pivot resistance must be monotonic"):
        BondCalibration(pivot_resistance_r3=0.25)
    with pytest.raises(ValueError, match="must be non-negative"):
        BondCalibration(conflict_penalty=-1.0)


def test_pivot_resistance_lookup_is_rank_specific_and_zero_below_r1():
    calibration = DEFAULT_BOND_CALIBRATION
    assert calibration.pivot_resistance(BondRank.LOCKED) == 0.0
    assert calibration.pivot_resistance(BondRank.R0) == 0.0
    assert calibration.pivot_resistance(BondRank.R1) == pytest.approx(0.5)
    assert calibration.pivot_resistance(BondRank.R5) == pytest.approx(7.0)
