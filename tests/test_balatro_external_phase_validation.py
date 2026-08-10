import pytest

from games.balatro.live.external import ColorGridSignature, PhaseTemplate
from games.balatro.live.external.phase_store import save_phase_templates
from games.balatro.live.external.phase_validation import (
    REQUIRED_PHASES,
    validate_template_set,
)


BASE_VALUES = {
    "BLIND_SELECT": 20,
    "ROUND_EVAL": 90,
    "SELECTING_HAND": 150,
    "SHOP": 220,
}


def _template(phase: str, offset=0, columns=2, rows=2):
    value = max(0, min(255, BASE_VALUES.get(phase, 0) + offset))
    return PhaseTemplate(
        phase=phase,
        signature=ColorGridSignature(
            columns=columns,
            rows=rows,
            values=tuple([value] * (columns * rows * 3)),
        ),
    )


def test_phase_validation_accepts_complete_template_set(tmp_path):
    path = tmp_path / "phases.json"
    save_phase_templates(
        path,
        [
            _template(phase, offset)
            for phase in sorted(REQUIRED_PHASES)
            for offset in (-1, 0, 1)
        ],
    )

    counts = validate_template_set(path)

    assert counts == {phase: 3 for phase in REQUIRED_PHASES}


def test_phase_validation_rejects_missing_phase(tmp_path):
    path = tmp_path / "phases.json"
    phases = sorted(REQUIRED_PHASES - {"SHOP"})
    save_phase_templates(
        path,
        [_template(phase, offset) for phase in phases for offset in (0, 1)],
    )

    with pytest.raises(ValueError, match="SHOP"):
        validate_template_set(path)


def test_phase_validation_rejects_inconsistent_grid_dimensions(tmp_path):
    path = tmp_path / "phases.json"
    templates = [
        _template(phase, offset)
        for phase in sorted(REQUIRED_PHASES)
        for offset in (0, 1)
    ]
    templates.append(_template("SHOP", columns=3, rows=2))
    save_phase_templates(path, templates)

    with pytest.raises(ValueError, match="inconsistent grid dimensions"):
        validate_template_set(path)


def test_phase_validation_rejects_undersampled_phase(tmp_path):
    path = tmp_path / "phases.json"
    templates = [
        _template(phase, offset)
        for phase in sorted(REQUIRED_PHASES)
        for offset in (0, 1)
    ]
    templates = [
        template
        for index, template in enumerate(templates)
        if not (template.phase == "SHOP" and index % 2 == 1)
    ]
    save_phase_templates(path, templates)

    with pytest.raises(ValueError, match="at least 2 samples"):
        validate_template_set(path)


def test_phase_validation_rejects_overlapping_phases(tmp_path):
    path = tmp_path / "phases.json"
    templates = [
        _template(phase, offset)
        for phase in sorted(REQUIRED_PHASES)
        for offset in (0, 1)
    ]
    templates = [
        PhaseTemplate(
            phase=template.phase,
            signature=ColorGridSignature(
                columns=2,
                rows=2,
                values=tuple([50] * 12),
            ),
        )
        for template in templates
    ]
    save_phase_templates(path, templates)

    with pytest.raises(ValueError, match="not visually separable"):
        validate_template_set(path)
