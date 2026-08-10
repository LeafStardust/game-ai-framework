from pathlib import Path

from games.balatro.live.external.card_recognition_validation import (
    validate_labeled_samples,
)


def test_committed_card_calibration_samples_are_recognized():
    root = Path(__file__).parents[1]
    results = validate_labeled_samples(
        root / "balatro-card-identities" / "labels.json",
        root / "balatro-card-templates.json",
    )

    assert len(results) == 8
    assert all(result["passed"] for result in results)
