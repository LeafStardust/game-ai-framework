import pytest

from games.balatro.live.external.card_live_validation import validate_recognitions
from games.balatro.live.external.card_recognition import CardLabelMatch, CardRecognition


def _recognition(rank, suit):
    return CardRecognition(
        rank=CardLabelMatch(rank, 0.1, 0.2, 0.9, None),
        suit=CardLabelMatch(suit, 0.1, 0.2, 0.9, None),
    )


def test_validate_recognitions_matches_compact_card_labels():
    results = validate_recognitions(
        ["JH", "10C", "8S"],
        [
            _recognition("J", "Hearts"),
            _recognition("10", "Clubs"),
            _recognition("8", "Spades"),
        ],
    )

    assert results == [True, True, True]


def test_validate_recognitions_reports_individual_failures():
    results = validate_recognitions(
        ["JH", "10C"],
        [_recognition("J", "Diamonds"), _recognition("9", "Clubs")],
    )

    assert results == [False, False]


def test_validate_recognitions_requires_same_card_count():
    with pytest.raises(ValueError, match="expected 2 cards, recognized 1"):
        validate_recognitions(["JH", "10C"], [_recognition("J", "Hearts")])
