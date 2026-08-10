import pytest

from games.balatro.live.external import ColorGridSignature, PhaseTemplate
from games.balatro.live.external.phase_store import save_phase_templates
from games.balatro.live.external.phase_validation import (
    REQUIRED_PHASES,
    validate_template_set,
)


def _template(phase: str, columns=2, rows=2):
    return PhaseTemplate(
        phase=phase,
        signature=ColorGridSignature(
            columns=columns,
            rows=rows,
            values=tuple([0] * (columns * rows * 3)),
        ),
    )


def test_phase_validation_accepts_complete_template_set(tmp_path):
    path = tmp_path / "phases.json"
    save_phase_templates(
        path,
        [
            _template(phase)
            for phase in sorted(REQUIRED_PHASES)
            for _ in range(3)
        ],
    )

    counts = validate_template_set(path)

    assert counts == {phase: 3 for phase in REQUIRED_PHASES}


def test_phase_validation_rejects_missing_phase(tmp_path):
    path = tmp_path / "phases.json"
    phases = sorted(REQUIRED_PHASES - {"SHOP"})
    save_phase_templates(path, [_template(phase) for phase in phases])

    with pytest.raises(ValueError, match="SHOP"):
        validate_template_set(path)


def test_phase_validation_rejects_inconsistent_grid_dimensions(tmp_path):
    path = tmp_path / "phases.json"
    templates = [_template(phase) for phase in sorted(REQUIRED_PHASES)]
    templates.append(_template("SHOP", columns=3, rows=2))
    save_phase_templates(path, templates)

    with pytest.raises(ValueError, match="inconsistent grid dimensions"):
        validate_template_set(path)
