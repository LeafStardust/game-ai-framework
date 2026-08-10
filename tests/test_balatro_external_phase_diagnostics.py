from games.balatro.live.external import ColorGridSignature, PhaseTemplate
from games.balatro.live.external.phase_diagnostics import (
    baseline_intra_phase_distance,
    cell_drift,
    centroid,
    nearest_phase_distances,
)


def _template(phase: str, values: tuple[int, ...]) -> PhaseTemplate:
    return PhaseTemplate(
        phase=phase,
        signature=ColorGridSignature(
            columns=2,
            rows=1,
            values=values,
        ),
    )


def test_nearest_phase_distances_prefers_matching_phase():
    baseline = [
        _template("A", (10, 10, 10, 200, 200, 200)),
        _template("A", (12, 12, 12, 198, 198, 198)),
        _template("B", (200, 200, 200, 10, 10, 10)),
        _template("B", (198, 198, 198, 12, 12, 12)),
    ]
    sample = _template("A", (11, 11, 11, 199, 199, 199))

    ranking = nearest_phase_distances(baseline, sample)

    assert ranking[0].phase == "A"
    assert ranking[0].raw < ranking[1].raw
    assert ranking[0].relative < ranking[1].relative


def test_centroid_averages_phase_signatures():
    result = centroid(
        [
            _template("A", (10, 20, 30, 40, 50, 60)),
            _template("A", (20, 30, 40, 50, 60, 70)),
        ]
    )

    assert result.values == (15, 25, 35, 45, 55, 65)


def test_cell_drift_reports_most_changed_cell_first():
    baseline = [
        _template("A", (10, 10, 10, 20, 20, 20)),
        _template("A", (10, 10, 10, 20, 20, 20)),
    ]
    diagnostic = [
        _template("A", (110, 110, 110, 20, 20, 20)),
        _template("A", (110, 110, 110, 20, 20, 20)),
    ]

    drifts = cell_drift(baseline, diagnostic)

    assert drifts[0].column == 0
    assert drifts[0].raw > drifts[1].raw


def test_baseline_intra_phase_distance_is_zero_for_identical_samples():
    templates = [
        _template("A", (10, 20, 30, 40, 50, 60)),
        _template("A", (10, 20, 30, 40, 50, 60)),
    ]

    raw, relative = baseline_intra_phase_distance(templates)

    assert raw == 0.0
    assert relative == 0.0
