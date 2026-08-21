from games.balatro.latest_zero_five_survival_policy import (
    OPENING_BANK_PACE_RATIO_FLOOR,
    should_bank_opening_play,
)


def test_opening_near_pace_hand_is_banked_before_discard_exhaustion():
    assert should_bank_opening_play(
        ante=1,
        best_pace_ratio=OPENING_BANK_PACE_RATIO_FLOOR,
        discards_remaining=4,
    )
    assert should_bank_opening_play(
        ante=2,
        best_pace_ratio=0.95,
        discards_remaining=1,
    )


def test_opening_bank_does_not_replace_strict_later_ante_policy():
    assert not should_bank_opening_play(
        ante=3,
        best_pace_ratio=0.95,
        discards_remaining=4,
    )


def test_opening_bank_does_not_fire_for_weak_or_already_full_pace_play():
    assert not should_bank_opening_play(
        ante=1,
        best_pace_ratio=OPENING_BANK_PACE_RATIO_FLOOR - 0.01,
        discards_remaining=4,
    )
    assert not should_bank_opening_play(
        ante=1,
        best_pace_ratio=1.0,
        discards_remaining=4,
    )
    assert not should_bank_opening_play(
        ante=1,
        best_pace_ratio=0.90,
        discards_remaining=0,
    )
