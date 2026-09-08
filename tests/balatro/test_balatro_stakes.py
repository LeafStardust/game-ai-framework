from games.balatro.adapter import BalatroAdapter
from games.balatro.decks import RED_DECK
from games.balatro.stakes import (
    STAKES,
    GOLD_STAKE,
    GREEN_STAKE,
    PURPLE_STAKE,
    RED_STAKE,
    WHITE_STAKE,
    BLUE_STAKE,
)


def test_all_balatro_stakes_are_registered_in_order():
    assert list(STAKES) == [
        "WHITE",
        "RED",
        "GREEN",
        "BLACK",
        "BLUE",
        "PURPLE",
        "ORANGE",
        "GOLD",
    ]


def test_red_deck_white_stake_keeps_four_discards():
    environment = BalatroAdapter(
        RED_DECK,
        WHITE_STAKE
    ).create_environment()

    assert environment.state.deck_name == "RED"
    assert environment.state.stake_name == "WHITE"
    assert environment.state.discards_remaining == 4


def test_red_deck_blue_stake_reduces_discards_to_three():
    environment = BalatroAdapter(
        RED_DECK,
        BLUE_STAKE
    ).create_environment()

    assert environment.state.discards_remaining == 3


def test_red_stake_removes_small_blind_reward():
    assert not RED_STAKE.small_blind_reward


def test_green_and_purple_stakes_use_expected_ante_requirements():
    assert GREEN_STAKE.requirement_for_ante(8, 50000) == 100000
    assert PURPLE_STAKE.requirement_for_ante(8, 50000) == 200000


def test_gold_stake_includes_all_joker_sticker_chances():
    assert GOLD_STAKE.eternal_joker_chance == 0.30
    assert GOLD_STAKE.perishable_joker_chance == 0.30
    assert GOLD_STAKE.rental_joker_chance == 0.30
