from games.balatro.live.adaptive_search import adaptive_blind_search_schedule


def test_opening_search_can_cover_one_discard_plus_all_four_hands():
    schedule = adaptive_blind_search_schedule(
        hands_remaining=4,
        discards_remaining=3,
    )

    assert schedule
    assert max(config.horizon for config in schedule) == 5


def test_no_discard_four_hand_state_does_not_add_fake_fifth_action():
    schedule = adaptive_blind_search_schedule(
        hands_remaining=4,
        discards_remaining=0,
    )

    assert schedule
    assert max(config.horizon for config in schedule) == 4
