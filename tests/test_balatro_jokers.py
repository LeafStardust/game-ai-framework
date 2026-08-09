import random

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.scoring import BalatroScorer, HandScore
from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.joker import JokerContext

from games.balatro.jokers.crazy_joker import CrazyJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.devious_joker import DeviousJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.greedy_joker import GreedyJoker
from games.balatro.jokers.lusty_joker import LustyJoker
from games.balatro.jokers.wrathful_joker import WrathfulJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.the_duo import TheDuoJoker
from games.balatro.jokers.the_trio import TheTrioJoker
from games.balatro.jokers.the_family import TheFamilyJoker
from games.balatro.jokers.the_order import TheOrderJoker
from games.balatro.jokers.the_tribe import TheTribeJoker
from games.balatro.jokers.blackboard import BlackboardJoker
from games.balatro.jokers.drivers_license import DriversLicenseJoker
from games.balatro.jokers.steel_joker import SteelJoker
from games.balatro.jokers.glass_joker import GlassJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.jokers.red_card import RedCardJoker
from games.balatro.jokers.castle import CastleJoker
from games.balatro.jokers.misprint import MisprintJoker
from games.balatro.jokers.ramen import RamenJoker
from games.balatro.jokers.vampire import VampireJoker
from games.balatro.jokers.hologram import HologramJoker
from games.balatro.jokers.fortune_teller import FortuneTellerJoker
from games.balatro.jokers.supernova import SupernovaJoker
from games.balatro.jokers.space_joker import SpaceJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.jokers.shoot_the_moon import ShootTheMoonJoker
from games.balatro.jokers.raised_fist import RaisedFistJoker
from games.balatro.jokers.seeing_double import SeeingDoubleJoker
from games.balatro.jokers.the_idol import TheIdolJoker
from games.balatro.jokers.bloodstone import BloodstoneJoker
from games.balatro.jokers.onyx_agate import OnyxAgateJoker
from games.balatro.jokers.arrowhead import ArrowheadJoker
from games.balatro.jokers.rough_gem import RoughGemJoker
from games.balatro.jokers.obelisk import ObeliskJoker
from games.balatro.jokers.hit_the_road import HitTheRoadJoker
from games.balatro.jokers.bootstraps import BootstrapsJoker


def test_jolly_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                JollyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.PAIR,
        state,
        cards
    )

    assert score.chips == 10
    assert score.mult == 10
    assert score.total == 100


def test_zany_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                ZanyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.THREE_OF_A_KIND,
        state,
        cards
    )

    assert score.chips == 30
    assert score.mult == 15
    assert score.total == 450


def test_mad_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                MadJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.TWO_PAIR,
        state,
        cards
    )

    assert score.chips == 20
    assert score.mult == 12
    assert score.total == 240


def test_crazy_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                CrazyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Clubs"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("6", "Hearts")
    ]

    score = scorer.score(
        PokerHand.STRAIGHT,
        state,
        cards
    )

    assert score.chips == 30
    assert score.mult == 16
    assert score.total == 480


def test_droll_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                DrollJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.FLUSH,
        state,
        cards
    )

    assert score.chips == 35
    assert score.mult == 14
    assert score.total == 490


def test_flat_mult_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                FlatMultJoker(4)
            ]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 6
    assert score.total == 60


def test_bull_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "money": 15,
            "jokers": [
                BullJoker()
            ]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 8
    assert score.total == 80


def test_sly_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                SlyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.PAIR,
        state,
        cards
    )

    assert score.chips == 60
    assert score.mult == 2
    assert score.total == 120


def test_wily_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                WilyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.THREE_OF_A_KIND,
        state,
        cards
    )

    assert score.chips == 130
    assert score.mult == 3
    assert score.total == 390


def test_clever_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                CleverJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.TWO_PAIR,
        state,
        cards
    )

    assert score.chips == 100
    assert score.mult == 2
    assert score.total == 200


def test_devious_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                DeviousJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Clubs"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("6", "Hearts")
    ]

    score = scorer.score(
        PokerHand.STRAIGHT,
        state,
        cards
    )

    assert score.chips == 130
    assert score.mult == 4
    assert score.total == 520


def test_crafty_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                CraftyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.FLUSH,
        state,
        cards
    )

    assert score.chips == 115
    assert score.mult == 4
    assert score.total == 460


def test_greedy_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                GreedyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Diamonds"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("5", "Hearts"),
        BalatroCard("3", "Clubs"),
        BalatroCard("2", "Spades")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 7
    assert score.total == 35


def test_lusty_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                LustyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("3", "Clubs"),
        BalatroCard("2", "Spades")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 7
    assert score.total == 35


def test_wrathful_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                WrathfulJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Spades"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("3", "Clubs"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 7
    assert score.total == 35


def test_gluttonous_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                GluttonousJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Clubs"),
        BalatroCard("7", "Clubs"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("3", "Hearts"),
        BalatroCard("2", "Spades")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 7
    assert score.total == 35


def test_even_steven_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                EvenStevenJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("4", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("A", "Diamonds"),
        BalatroCard("K", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 9
    assert score.total == 45


def test_odd_todd_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                OddToddJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 98
    assert score.mult == 1
    assert score.total == 98


def test_fibonacci_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                FibonacciJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("2", "Spades"),
        BalatroCard("5", "Clubs"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("Q", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 25
    assert score.total == 125


def test_scholar_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                ScholarJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.PAIR,
        state,
        cards
    )

    assert score.chips == 50
    assert score.mult == 10
    assert score.total == 500


def test_half_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                HalfJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Spades"),
        BalatroCard("Q", "Clubs")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 21
    assert score.total == 105


def test_half_joker_does_not_trigger_above_three_cards():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                HalfJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Spades"),
        BalatroCard("Q", "Clubs"),
        BalatroCard("J", "Diamonds")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 1
    assert score.total == 5


def test_banner_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "discards_remaining": 3,
            "jokers": [
                BannerJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 95
    assert score.mult == 1
    assert score.total == 95


def test_the_duo_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                TheDuoJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.PAIR,
        state,
        cards
    )

    assert score.chips == 10
    assert score.mult == 2
    assert score.x_mult == 2
    assert score.total == 40


def test_the_trio_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                TheTrioJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.THREE_OF_A_KIND,
        state,
        cards
    )

    assert score.chips == 30
    assert score.mult == 3
    assert score.x_mult == 3
    assert score.total == 270


def test_the_family_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                TheFamilyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Clubs"),
        BalatroCard("A", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.FOUR_OF_A_KIND,
        state,
        cards
    )

    assert score.chips == 60
    assert score.mult == 7
    assert score.x_mult == 4
    assert score.total == 1680


def test_the_order_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                TheOrderJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Clubs"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("6", "Hearts")
    ]

    score = scorer.score(
        PokerHand.STRAIGHT,
        state,
        cards
    )

    assert score.chips == 30
    assert score.mult == 4
    assert score.x_mult == 3
    assert score.total == 360


def test_the_tribe_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                TheTribeJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.FLUSH,
        state,
        cards
    )

    assert score.chips == 35
    assert score.mult == 4
    assert score.x_mult == 2
    assert score.total == 280


def test_blackboard_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                BlackboardJoker()
            ],
            "hand": [
                BalatroCard("A", "Spades"),
                BalatroCard("K", "Clubs"),
                BalatroCard("Q", "Spades")
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Diamonds"),
    ]

    score = scorer.score(
        PokerHand.PAIR,
        state,
        cards
    )

    assert score.chips == 10
    assert score.mult == 2
    assert score.x_mult == 3
    assert score.total == 60


def test_blackboard_joker_does_not_trigger_with_other_suit():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                BlackboardJoker()
            ],
            "hand": [
                BalatroCard("A", "Spades"),
                BalatroCard("K", "Clubs"),
                BalatroCard("Q", "Hearts")
            ]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 2
    assert score.x_mult == 1.0
    assert score.total == 20


def test_drivers_license_joker():

    scorer = BalatroScorer()

    deck = [
        BalatroCard(str(rank), "Hearts")
        for rank in range(2, 19)
    ]

    for card in deck:
        card.enhancement = "Steel"

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                DriversLicenseJoker()
            ],
            "deck": deck
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 2
    assert score.x_mult == 3
    assert score.total == 60


def test_steel_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                SteelJoker()
            ],
            "deck": [
                BalatroCard("A", "Hearts", "Steel"),
                BalatroCard("K", "Spades", "Steel"),
                BalatroCard("Q", "Clubs")
            ]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 2
    assert score.x_mult == 1.4
    assert score.total == 28


def test_glass_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "glass_cards_destroyed": 2,
            "jokers": [
                GlassJoker()
            ]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 2
    assert score.x_mult == 2.5
    assert score.total == 50


def test_ride_the_bus_joker():

    scorer = BalatroScorer()

    joker = RideTheBusJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker]
        }
    )()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("4", "Spades"),
        BalatroCard("7", "Clubs")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.mult == 2

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.mult == 3


def test_ride_the_bus_joker_resets_on_face_card():

    scorer = BalatroScorer()

    joker = RideTheBusJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker]
        }
    )()

    cards = [
        BalatroCard("J", "Hearts"),
        BalatroCard("4", "Spades")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.mult == 1


def test_green_joker():

    scorer = BalatroScorer()

    joker = GreenJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": []
        }
    )()

    cards = [
        BalatroCard("A", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.mult == 2

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.mult == 3


def test_red_card_joker():

    scorer = BalatroScorer()

    joker = RedCardJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": []
        }
    )()

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.BOOSTER_SKIPPED
        )
    )

    joker.apply(context)

    assert joker.mult == 3

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.VOUCHER_SKIPPED
        )
    )

    joker.apply(context)

    assert joker.mult == 6


def test_castle_joker():

    joker = CastleJoker("Spades")

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": []
        }
    )()

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.CARDS_DISCARDED,
            [
                BalatroCard("A", "Spades"),
                BalatroCard("7", "Hearts"),
                BalatroCard("K", "Spades")
            ]
        )
    )

    joker.apply(context)

    assert joker.chips == 6

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.CARDS_DISCARDED,
            [
                BalatroCard("2", "Spades")
            ]
        )
    )

    joker.apply(context)

    assert joker.chips == 9


def test_misprint_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [MisprintJoker()]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert 2 <= score.mult <= 25


def test_ramen_joker():

    joker = RamenJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": []
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Spades")
    ]

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.CARDS_DISCARDED,
            cards
        )
    )

    joker.apply(context)

    assert joker.x_mult == 1.98


def test_vampire_joker():

    joker = VampireJoker()

    card = BalatroCard(
        "A",
        "Hearts",
        enhancement="BONUS"
    )

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": []
        }
    )()

    context = JokerContext(
        state=state,
        cards=[card]
    )

    joker.apply(context)

    assert joker.x_mult == 1.1
    assert card.enhancement is None


def test_hologram_joker():

    joker = HologramJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": []
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Spades")
    ]

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.CARDS_ADDED,
            cards
        )
    )

    joker.apply(context)

    assert joker.x_mult == 1.5


def test_fortune_teller_joker():

    joker = FortuneTellerJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": []
        }
    )()

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.TAROT_USED
        )
    )

    joker.apply(context)
    joker.apply(context)

    assert joker.mult == 2


def test_supernova_joker():

    joker = SupernovaJoker(PokerHand.PAIR)

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": []
        }
    )()

    context = JokerContext(
        state=state,
        poker_hand=PokerHand.PAIR
    )

    joker.apply(context)
    joker.apply(context)

    assert joker.mult == 2


def test_space_joker():

    joker = SpaceJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": []
        }
    )()

    context = JokerContext(
        state=state,
        poker_hand=PokerHand.PAIR
    )

    random.seed(1)

    joker.apply(context)

    assert "level_ups" in context.data


def test_splash_joker():

    joker = SplashJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": []
        }
    )()

    context = JokerContext(
        state=state
    )

    joker.apply(context)

    assert context.data["all_cards_score"] is True


def test_shoot_the_moon_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [ShootTheMoonJoker()]
        }
    )()

    cards = [
        BalatroCard("Q", "Hearts"),
        BalatroCard("7", "Spades")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.mult == 14


def test_raised_fist_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [RaisedFistJoker()],
            "hand": [
                BalatroCard("7", "Hearts"),
                BalatroCard("K", "Spades"),
                BalatroCard("3", "Clubs")
            ]
        }
    )()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state
    )

    assert score.mult == 7


def test_seeing_double_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [SeeingDoubleJoker()]
        }
    )()

    cards = [
        BalatroCard("A", "Clubs"),
        BalatroCard("7", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.x_mult == 2.0


def test_the_idol_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [TheIdolJoker("A", "Spades")]
        }
    )()

    cards = [
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.x_mult == 2.0


def test_bloodstone_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [BloodstoneJoker()]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts")
    ]

    random.seed(1)

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.x_mult == 1.5


def test_onyx_agate_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [OnyxAgateJoker()]
        }
    )()

    cards = [
        BalatroCard("A", "Clubs"),
        BalatroCard("7", "Clubs"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.mult == 15


def test_arrowhead_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [ArrowheadJoker()]
        }
    )()

    cards = [
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Spades"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 105


def test_rough_gem_joker():

    joker = RoughGemJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker]
        }
    )()

    cards = [
        BalatroCard("A", "Diamonds"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    context = JokerContext(
        state=state,
        cards=cards
    )

    joker.apply(context)

    assert context.data["money"] == 2


def test_obelisk_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [ObeliskJoker()]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades")
    ]

    score = scorer.score(
        PokerHand.PAIR,
        state,
        cards
    )

    assert score.x_mult == 1.2


def test_obelisk_joker_resets_on_most_played_hand():

    joker = ObeliskJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker]
        }
    )()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        poker_hand=PokerHand.PAIR,
        data={
            "most_played_hand": PokerHand.PAIR
        }
    )

    joker.x_mult = 2.0
    joker.apply(context)

    assert joker.x_mult == 1.0
    assert context.score.x_mult == 1.0


def test_hit_the_road_joker():

    joker = HitTheRoadJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker]
        }
    )()

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.CARDS_DISCARDED,
            [
                BalatroCard("J", "Hearts"),
                BalatroCard("J", "Spades"),
                BalatroCard("7", "Clubs")
            ]
        )
    )

    joker.apply(context)

    assert joker.x_mult == 2.0


def test_hit_the_road_joker_no_jacks():

    joker = HitTheRoadJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker]
        }
    )()

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.CARDS_DISCARDED,
            [
                BalatroCard("7", "Hearts"),
                BalatroCard("8", "Spades")
            ]
        )
    )

    joker.apply(context)

    assert joker.x_mult == 1.0


def test_bootstraps_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "money": 15,
            "jokers": [BootstrapsJoker()]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 13
    assert score.mult == 8
    assert score.total == 104


def test_bootstraps_joker_below_five_dollars():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "money": 4,
            "jokers": [BootstrapsJoker()]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 2
    assert score.total == 20