from games.balatro.strategy_plan_pack_policy import _playing_card_matches


def test_strategy_plan_pack_goals_match_rank_and_enhancement_targets() -> None:
    assert _playing_card_matches("kings", {"rank": "King", "suit": "Hearts"})
    assert not _playing_card_matches("kings", {"rank": "Queen", "suit": "Hearts"})
    assert _playing_card_matches("steel", {"rank": "7", "enhancement": "m_steel"})
    assert _playing_card_matches("glass", {"rank": "7", "enhancement": "m_glass"})
    assert _playing_card_matches("gold_economy", {"rank": "7", "enhancement": "m_gold"})


def test_strategy_plan_pack_goals_match_suit_and_low_rank_targets() -> None:
    assert _playing_card_matches("hearts", {"rank": "9", "suit": "Hearts"})
    assert _playing_card_matches("low_ranks", {"rank": "4", "suit": "Clubs"})
    assert not _playing_card_matches("low_ranks", {"rank": "8", "suit": "Clubs"})
