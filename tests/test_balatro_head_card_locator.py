from games.balatro.live.external.head_card_locator import (
    _candidate_from_component,
    _choose_dominant_family,
)
from games.balatro.live.external.viewport import PixelRect


def _candidate(left, top, width, height, density=0.5):
    candidate = _candidate_from_component(
        PixelRect(left, top, width, height),
        density,
        8,
    )
    assert candidate is not None
    return candidate


def test_head_locator_prefers_widest_repeated_same_row_observation():
    candidates = [
        _candidate(192, 74, 800, 188, 0.455),
        _candidate(192, 74, 802, 188, 0.473),
        _candidate(192, 74, 802, 188, 0.473),
        _candidate(174, 74, 846, 188, 0.564),
    ]

    chosen = _choose_dominant_family(candidates)

    assert chosen is not None
    assert chosen.left == 174
    assert chosen.width == 846
    assert chosen.height == 188


def test_head_locator_rejects_equally_supported_separate_row_families():
    candidates = [
        _candidate(174, 74, 846, 188),
        _candidate(176, 76, 842, 188),
        _candidate(174, 310, 846, 188),
        _candidate(176, 312, 842, 188),
    ]

    assert _choose_dominant_family(candidates) is None


def test_head_locator_rejects_implausible_expected_count_split():
    # 846x262 split into eight slots produces a stride/height ratio below the
    # accepted Balatro hand range; this mirrors the overgrown lowest-threshold
    # component seen in the live Head diagnostic.
    candidate = _candidate_from_component(
        PixelRect(174, 0, 846, 262),
        0.492,
        8,
    )

    assert candidate is None
