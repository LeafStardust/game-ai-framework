import pytest

from games.balatro.bonds.strategy_plan import _completion_fraction


def test_motif_free_strategy_completion_uses_full_bond_fraction():
    assert _completion_fraction(
        bond_fraction=1.0,
        present_components=(),
        missing_components=(),
    ) == pytest.approx(1.0)

    assert _completion_fraction(
        bond_fraction=0.5,
        present_components=(),
        missing_components=(),
    ) == pytest.approx(0.5)


def test_motif_strategy_completion_keeps_bond_component_blend():
    completion = _completion_fraction(
        bond_fraction=1.0,
        present_components=("BARON", "MIME"),
        missing_components=("STEEL", "KINGS"),
    )

    assert completion == pytest.approx(0.55 + 0.45 * 0.5)
