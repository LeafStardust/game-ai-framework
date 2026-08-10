from pathlib import Path

from games.balatro.live.external.card_recognition_validation import (
    validate_labeled_samples,
)


def _validate(root: Path, directory: str):
    return validate_labeled_samples(
        root / directory / "labels.json",
        root / "balatro-card-templates.json",
    )


def test_committed_card_calibration_samples_are_recognized():
    root = Path(__file__).parents[1]

    for directory in (
        "balatro-card-identities",
        "balatro-card-identities-02",
        "balatro-card-identities-03",
    ):
        results = _validate(root, directory)
        assert len(results) == 8
        assert all(result["passed"] for result in results)


def test_failed_unseen_hand_remains_a_holdout_regression():
    root = Path(__file__).parents[1]
    results = _validate(root, "balatro-card-unseen-01")

    assert len(results) == 8
    assert all(result["passed"] for result in results)
