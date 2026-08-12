from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.canio import CanioJoker
from games.balatro.jokers.constellation import ConstellationJoker
from games.balatro.jokers.egg import EggJoker
from games.balatro.jokers.flash_card import FlashCardJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.jokers.ice_cream import IceCreamJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.loyalty_card import LoyaltyCardJoker
from games.balatro.jokers.lucky_cat import LuckyCatJoker
from games.balatro.jokers.obelisk import ObeliskJoker
from games.balatro.jokers.red_card import RedCardJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.jokers.runner import RunnerJoker
from games.balatro.jokers.seltzer import SeltzerJoker
from games.balatro.jokers.spare_trousers import SpareTrousersJoker
from games.balatro.jokers.vampire import VampireJoker
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.external.save_observer import _normalize_item
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(hand, deck=None, *, target=1000, hands=2, discards=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(hand)
    state.deck = list(deck or [])
    state.score = 0
    state.hands_remaining = hands
    state.discards_remaining = discards
    state.blind = Blind(BlindType.BIG, target)
    return state


def test_ice_cream_projection_scores_and_decays_only_copied_joker():
    cards = [
        BalatroCard("K", "Spades", live_id=0),
        BalatroCard("K", "Diamonds", live_id=1),
    ]
    state = _state(cards)
    ice_cream = IceCreamJoker()
    state.jokers = [ice_cream]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert transition.distribution.minimum == 260
    assert transition.joker_projection_complete is True
    assert ice_cream.chips == 100
    assert transition.state_after_scoring is not state
    assert transition.state_after_scoring.hand is not state.hand
    assert transition.state_after_scoring.hand[0] is cards[0]
    assert transition.state_after_scoring.hand[1] is cards[1]
    assert transition.state_after_scoring.jokers[0] is not ice_cream
    assert transition.state_after_scoring.jokers[0].chips == 95


def test_green_joker_projection_starts_from_hydrated_mult_and_updates_only_copy():
    cards = [
        BalatroCard("K", "Spades", live_id=0),
        BalatroCard("K", "Diamonds", live_id=1),
    ]
    state = _state(cards)
    green = GreenJoker()
    green.mult = 19
    state.jokers = [green]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert transition.distribution.minimum == 660
    assert transition.distribution.maximum == 660
    assert transition.joker_projection_complete is True
    assert green.mult == 19
    assert transition.state_after_scoring.jokers[0].mult == 20


def test_runner_projection_starts_from_hydrated_chips_and_carries_growth():
    cards = [
        BalatroCard("2", "Spades", live_id=0),
        BalatroCard("3", "Hearts", live_id=1),
        BalatroCard("4", "Clubs", live_id=2),
        BalatroCard("5", "Diamonds", live_id=3),
        BalatroCard("6", "Spades", live_id=4),
    ]
    state = _state(cards)
    runner = RunnerJoker()
    runner.chips = 45
    state.jokers = [runner]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.STRAIGHT,
        state,
        cards,
    )

    assert transition.distribution.minimum == 440
    assert transition.distribution.maximum == 440
    assert transition.joker_projection_complete is True
    assert runner.chips == 45
    assert transition.state_after_scoring.jokers[0].chips == 60


def test_hydrated_read_only_jokers_use_current_live_values():
    ace = BalatroCard("A", "Spades")
    state = _state([ace])

    constellation = ConstellationJoker()
    constellation.x_mult = 2.0
    flash = FlashCardJoker()
    flash.mult = 5
    state.jokers = [flash, constellation]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.distribution.minimum == 192
    assert transition.distribution.maximum == 192
    assert transition.joker_projection_complete is True
    assert flash.mult == 5
    assert constellation.x_mult == 2.0
    assert transition.state_after_scoring.jokers[0].mult == 5
    assert transition.state_after_scoring.jokers[1].x_mult == 2.0


def test_spare_trousers_growth_starts_from_hydrated_mult_on_branch_only():
    cards = [
        BalatroCard("2", "Spades"),
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Clubs"),
        BalatroCard("3", "Diamonds"),
    ]
    state = _state(cards)
    trousers = SpareTrousersJoker()
    trousers.mult = 6
    state.jokers = [trousers]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.TWO_PAIR,
        state,
        cards,
    )

    assert transition.distribution.minimum == 300
    assert transition.joker_projection_complete is True
    assert trousers.mult == 6
    assert transition.state_after_scoring.jokers[0].mult == 8


def test_hydrated_non_scoring_joker_does_not_block_exact_score_projection():
    ace = BalatroCard("A", "Spades")
    state = _state([ace])
    egg = EggJoker()
    egg.sell_value = 15
    state.jokers = [egg]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.distribution.minimum == 16
    assert transition.joker_projection_complete is True
    assert egg.sell_value == 15
    assert transition.state_after_scoring.jokers[0].sell_value == 15


def test_red_card_projection_applies_accumulated_hydrated_mult():
    ace = BalatroCard("A", "Spades")
    state = _state([ace])
    red_card = RedCardJoker()
    red_card.mult = 12
    state.jokers = [red_card]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.distribution.minimum == 208
    assert transition.distribution.maximum == 208
    assert transition.joker_projection_complete is True
    assert red_card.mult == 12
    assert transition.state_after_scoring.jokers[0].mult == 12


def test_ride_the_bus_ignores_non_scoring_face_cards():
    ace = BalatroCard("A", "Spades")
    king = BalatroCard("K", "Hearts")
    state = _state([ace, king])
    ride_bus = RideTheBusJoker()
    ride_bus.mult = 8
    state.jokers = [ride_bus]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace, king],
    )

    # Only the Ace scores. The non-scoring King must not reset Ride the Bus.
    # 16 Chips * (1 base Mult + 9 Ride the Bus Mult) = 160.
    assert transition.distribution.minimum == 160
    assert transition.joker_projection_complete is True
    assert ride_bus.mult == 8
    assert transition.state_after_scoring.jokers[0].mult == 9


def test_obelisk_resets_on_any_tied_most_played_hand_and_carries_history():
    ace = BalatroCard("A", "Spades")
    state = _state([ace])
    state.hand_play_counts[PokerHand.HIGH_CARD.value] = 4
    state.hand_play_counts[PokerHand.PAIR.value] = 4
    obelisk = ObeliskJoker()
    obelisk.x_mult = 2.4
    state.jokers = [obelisk]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.distribution.minimum == 16
    assert transition.joker_projection_complete is True
    assert obelisk.x_mult == 2.4
    assert state.hand_play_counts[PokerHand.HIGH_CARD.value] == 4
    assert transition.state_after_scoring.jokers[0].x_mult == 1.0
    assert transition.state_after_scoring.hand_play_counts[PokerHand.HIGH_CARD.value] == 5


def test_loyalty_card_sixth_hand_transition_is_projected_on_copy():
    ace = BalatroCard("A", "Spades")
    state = _state([ace])
    loyalty = LoyaltyCardJoker()
    loyalty.hands = 5
    state.jokers = [loyalty]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.distribution.minimum == 64
    assert transition.distribution.maximum == 64
    assert transition.joker_projection_complete is True
    assert loyalty.hands == 5
    assert transition.state_after_scoring.jokers[0].hands == 6


def test_vampire_removes_only_scoring_enhancements_on_isolated_cards():
    ace = BalatroCard("A", "Spades", enhancement="Mult")
    king = BalatroCard("K", "Hearts", enhancement="Bonus")
    state = _state([ace, king])
    vampire = VampireJoker()
    vampire.x_mult = 1.0
    state.jokers = [vampire]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace, king],
    )

    # Vampire strips the scoring Ace before its +4 Mult can apply, grows to x1.1,
    # and leaves the non-scoring enhanced King untouched.
    assert transition.distribution.minimum == 17
    assert transition.joker_projection_complete is True
    assert ace.enhancement == "Mult"
    assert king.enhancement == "Bonus"
    assert transition.state_after_scoring.hand[0] is not ace
    assert transition.state_after_scoring.hand[0].enhancement is None
    assert transition.state_after_scoring.hand[1].enhancement == "Bonus"
    assert vampire.x_mult == 1.0
    assert transition.state_after_scoring.jokers[0].x_mult == 1.1


def test_bootstraps_projection_adds_only_mult_from_public_money():
    ace = BalatroCard("A", "Spades", live_id=0)
    state = _state([ace])
    state.money = 5
    bootstraps = BootstrapsJoker()
    state.jokers = [bootstraps]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.distribution.minimum == 48
    assert transition.distribution.maximum == 48
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert state.money == 5
    assert transition.state_after_scoring.money == 5
    assert transition.state_after_scoring.jokers[0] is not bootstraps


def test_bootstraps_and_ice_cream_project_together_without_mutating_observed_state():
    cards = [
        BalatroCard("K", "Spades", live_id=0),
        BalatroCard("K", "Diamonds", live_id=1),
    ]
    state = _state(cards)
    state.money = 5
    ice_cream = IceCreamJoker()
    ice_cream.chips = 85
    bootstraps = BootstrapsJoker()
    state.jokers = [ice_cream, bootstraps]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert transition.distribution.minimum == 460
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert ice_cream.chips == 85
    assert transition.state_after_scoring.jokers[0].chips == 80
    assert isinstance(transition.state_after_scoring.jokers[1], BootstrapsJoker)


def test_two_action_planner_carries_ice_cream_decay_into_second_play():
    ace = BalatroCard("A", "Spades", live_id=0)
    state = _state(
        [ace],
        [BalatroCard("K", "Hearts")],
        target=1000,
        hands=2,
        discards=0,
    )
    ice_cream = IceCreamJoker()
    state.jokers = [ice_cream]

    planner = LiveBlindClearPlanner(
        play_width=1,
        discard_width=0,
        horizon=2,
    )
    plan = planner.plan(state)

    assert plan.action.name == PLAY_CARDS
    assert plan.value.expected_score == 226.0
    assert plan.exact is True
    assert ice_cream.chips == 100


def test_final_hydrated_projection_jokers_are_admitted_together():
    ace = BalatroCard("A", "Spades")
    state = _state([ace])

    canio = CanioJoker()
    canio.x_mult = 3.0
    lucky_cat = LuckyCatJoker()
    lucky_cat.x_mult = 2.0
    seltzer = SeltzerJoker()
    seltzer.rounds_remaining = 7

    state.jokers = [canio, lucky_cat, seltzer]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    # Seltzer retriggers the Ace once: 5 base + 22 card Chips = 27. Canio x3 and
    # Lucky Cat x2 then give 27 * 1 * 6 = 162.
    assert transition.distribution.minimum == 162
    assert transition.distribution.maximum == 162
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert canio.x_mult == 3.0
    assert lucky_cat.x_mult == 2.0
    assert seltzer.rounds_remaining == 7
    assert transition.state_after_scoring.jokers[2].rounds_remaining == 6


def test_unsupported_joker_is_reported_and_not_silently_applied():
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Diamonds"),
    ]
    state = _state(cards)
    state.jokers = [JollyJoker()]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert transition.distribution.minimum == 60
    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("Jolly",)


def test_ice_cream_public_save_state_is_narrowly_whitelisted_and_restored():
    normalized = _normalize_item(
        {
            "sort_id": 77,
            "label": "Ice Cream",
            "save_fields": {"center": "j_ice_cream"},
            "ability": {
                "name": "Ice Cream",
                "set": "Joker",
                "extra": {
                    "chips": 65,
                    "chip_mod": 5,
                    "private_test_field": 12345,
                },
            },
        }
    )

    assert normalized["public_state"] == {
        "chips": 65,
        "chip_mod": 5,
    }
    assert "ability" not in normalized
    assert "private_test_field" not in normalized["public_state"]

    joker = LiveJokerFactory().create(normalized)
    assert isinstance(joker, IceCreamJoker)
    assert joker.chips == 65
    assert joker.chip_mod == 5
    assert joker.live_id == 77
