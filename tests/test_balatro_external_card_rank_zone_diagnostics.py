from games.balatro.live.external.card_rank_zone_diagnostics import (
    RankZoneScore,
    candidate_rank_zones,
    rank_zone_sort_key,
)


def test_candidate_rank_zones_stay_above_suit_glyph_band():
    zones = candidate_rank_zones()

    assert zones
    assert all(top + height < 0.30 for _, top, _, height in zones)


def test_rank_zone_sort_prefers_generalization_then_separation():
    better_accuracy = RankZoneScore(
        (0.06, 0.12, 0.28, 0.16),
        7,
        8,
        2,
        0.10,
        0.01,
    )
    fewer_collisions = RankZoneScore(
        (0.08, 0.12, 0.28, 0.16),
        6,
        8,
        0,
        0.05,
        0.02,
    )

    assert rank_zone_sort_key(better_accuracy) < rank_zone_sort_key(fewer_collisions)

    first = RankZoneScore(
        (0.06, 0.12, 0.28, 0.16),
        6,
        8,
        0,
        0.04,
        0.02,
    )
    second = RankZoneScore(
        (0.08, 0.12, 0.28, 0.16),
        6,
        8,
        1,
        0.01,
        0.04,
    )

    assert rank_zone_sort_key(first) < rank_zone_sort_key(second)
