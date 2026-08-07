from games.balatro.hand import PokerHand


def test_poker_hand_types_exist():

    assert PokerHand.PAIR.value == "PAIR"
    assert PokerHand.FLUSH.value == "FLUSH"
    assert PokerHand.FULL_HOUSE.value == "FULL_HOUSE"