from games.balatro.live.external.card_rank_fixed_diagnostics import (
    candidate_fixed_rank_zones,
    fixed_rank_signature,
    fixed_rank_sort_key,
    shifted_rank_distance,
    FixedRankScore,
)
from games.balatro.live.external.card_templates import RGBImage


def _image(width=20, height=20, *, offset_x=0, value=(30, 30, 30)):
    rgb = bytearray(b"\xf0\xf0\xf0" * (width * height))
    for y in range(6, 12):
        for x in range(5 + offset_x, 9 + offset_x):
            index = (y * width + x) * 3
            rgb[index : index + 3] = bytes(value)
    return RGBImage(width, height, bytes(rgb))


def test_candidate_fixed_rank_zones_stay_in_diagnostic_search_band():
    zones = candidate_fixed_rank_zones()

    assert zones
    assert all(0.06 <= left <= 0.10 for left, _, _, _ in zones)
    assert all(0.12 <= top <= 0.16 for _, top, _, _ in zones)
    assert all(0.28 <= width <= 0.36 for _, _, width, _ in zones)
    assert all(0.10 <= height <= 0.14 for _, _, _, height in zones)


def test_fixed_rank_signature_is_color_normalized():
    zone = (0.0, 0.0, 1.0, 1.0)
    first = fixed_rank_signature(_image(value=(20, 20, 20)), zone, mode="strength")
    second = fixed_rank_signature(_image(value=(120, 40, 40)), zone, mode="strength")

    assert first == second


def test_shifted_rank_distance_tolerates_one_cell_translation():
    columns = 4
    rows = 3
    first = (
        0, 255, 0, 0,
        0, 255, 0, 0,
        0, 0, 0, 0,
    )
    shifted = (
        0, 0, 255, 0,
        0, 0, 255, 0,
        0, 0, 0, 0,
    )

    assert shifted_rank_distance(
        first,
        shifted,
        columns=columns,
        rows=rows,
        max_shift=1,
    ) == 0.0


def test_fixed_rank_sort_prefers_accuracy_then_collisions():
    better_accuracy = FixedRankScore((0, 0, 1, 1), "binary", 9, 10, 3, 0.2, 0.1)
    fewer_collisions = FixedRankScore((0, 0, 1, 1), "strength", 8, 10, 0, 0.1, 0.2)

    assert fixed_rank_sort_key(better_accuracy) < fixed_rank_sort_key(fewer_collisions)
