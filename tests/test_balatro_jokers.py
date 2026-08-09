import random

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.scoring import BalatroScorer, HandScore
from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.joker import JokerContext
from framework.core.state import GameState

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
from games.balatro.jokers.canio import CanioJoker
from games.balatro.jokers.campfire import CampfireJoker
from games.balatro.jokers.cavendish import CavendishJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.flash_card import FlashCardJoker
from games.balatro.jokers.loyalty_card import LoyaltyCardJoker
from games.balatro.jokers.mystic_summit import MysticSummitJoker
from games.balatro.jokers.perkeo import PerkeoJoker
from games.balatro.jokers.triboulet import TribouletJoker
from games.balatro.jokers.yorick import YorickJoker
from games.balatro.jokers.astronaut import AstronautJoker
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.certificate import CertificateJoker
from games.balatro.jokers.cartomancer import CartomancerJoker
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.marble_joker import MarbleJoker
from games.balatro.jokers.seance import SeanceJoker
from games.balatro.jokers.sixth_sense import SixthSenseJoker
from games.balatro.jokers.trading_card import TradingCardJoker
from games.balatro.jokers.vagabond import VagabondJoker
from games.balatro.jokers.eight_ball import EightBallJoker
from games.balatro.jokers.hanging_chad import HangingChadJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.jokers.sock_and_buskin import SockAndBuskinJoker
from games.balatro.jokers.flower_pot import FlowerPotJoker
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.midas_mask import MidasMaskJoker
from games.balatro.jokers.runner import RunnerJoker
from games.balatro.jokers.shortcut import ShortcutJoker
from games.balatro.jokers.smeared_joker import SmearedJoker
from games.balatro.jokers.wee_joker import WeeJoker
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.acrobat import AcrobatJoker
from games.balatro.jokers.cloud_9 import Cloud9Joker
from games.balatro.jokers.delayed_gratification import DelayedGratificationJoker
from games.balatro.jokers.egg import EggJoker
from games.balatro.jokers.gift_card import GiftCardJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.reserved_parking import ReservedParkingJoker
from games.balatro.jokers.rocket import RocketJoker
from games.balatro.jokers.to_do_list import ToDoListJoker
from games.balatro.jokers.ancient_joker import AncientJoker
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.brainstorm import BrainstormJoker
from games.balatro.jokers.golden_ticket import GoldenTicketJoker
from games.balatro.jokers.invisible_joker import InvisibleJoker
from games.balatro.jokers.joker_stencil import JokerStencil
from games.balatro.jokers.luchador import LuchadorJoker
from games.balatro.jokers.mr_bones import MrBonesJoker
from games.balatro.jokers.madness import MadnessJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.satellite import SatelliteJoker
from games.balatro.jokers.swashbuckler import SwashbucklerJoker
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.jokers.coupon_tag import CouponTagJoker
from games.balatro.jokers.diet_cola import DietColaJoker
from games.balatro.jokers.hallucination import HallucinationJoker
from games.balatro.jokers.hiker import HikerJoker
from games.balatro.jokers.merry_andy import MerryAndyJoker
from games.balatro.jokers.showman import ShowmanJoker
from games.balatro.jokers.stone_joker import StoneJoker
from games.balatro.jokers.turtle_bean import TurtleBeanJoker


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


def test_canio_joker():
    joker = CanioJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        data={
            "destroyed_cards": [
                BalatroCard("K", "Hearts")
            ]
        }
    )

    joker.apply(context)

    assert joker.x_mult == 2.0
    assert context.score.x_mult == 2.0


def test_triboulet_joker():
    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {"jokers": [TribouletJoker()]}
    )()

    cards = [
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Spades")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.x_mult == 4.0


def test_yorick_joker():
    joker = YorickJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    cards = [
        BalatroCard("2", "Hearts")
        for _ in range(23)
    ]

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.CARDS_DISCARDED,
            cards
        )
    )

    joker.apply(context)

    assert joker.discarded_cards == 0
    assert joker.x_mult == 6.0


def test_chicot_joker():
    joker = ChicotJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(state=state)

    joker.apply(context)

    assert context.data["disable_boss_blind"] is True


def test_perkeo_joker():
    joker = PerkeoJoker()

    consumable = object()

    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.ROUND_ENDED
        ),
        data={
            "consumables": [consumable]
        }
    )

    joker.apply(context)

    assert context.data["create_negative_copy"] is consumable


def test_campfire_joker():
    joker = CampfireJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.CARD_SOLD
        )
    )

    joker.apply(context)

    assert joker.x_mult == 1.25


def test_cavendish_joker():
    joker = CavendishJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2)
    )

    joker.apply(context)

    assert context.score.x_mult == 3.0
    assert joker.active is True


def test_loyalty_card_joker():
    joker = LoyaltyCardJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    for _ in range(6):
        context = JokerContext(
            state=state,
            score=HandScore(10, 2)
        )
        joker.apply(context)

    assert context.score.x_mult == 4.0


def test_flash_card_joker():

    joker = FlashCardJoker()

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
        data={"rerolls": 3}
    )

    joker.apply(context)

    assert context.score.mult == 8


def test_mystic_summit_joker():
    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [MysticSummitJoker()],
            "discards_remaining": 0
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.mult == 17


def test_astronaut_joker(monkeypatch):

    monkeypatch.setattr(
        "games.balatro.jokers.astronaut.random.random",
        lambda: 0.1
    )

    joker = AstronautJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        poker_hand=PokerHand.PAIR
    )

    joker.apply(context)

    assert context.data["level_up_hand"] == PokerHand.PAIR


def test_burnt_joker():

    joker = BurntJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    card = BalatroCard("A", "Hearts")

    context = JokerContext(
        state=state,
        event=BalatroEvent(
            BalatroEventType.CARDS_DISCARDED,
            [card]
        ),
        data={"discarded_hand": PokerHand.PAIR}
    )

    joker.apply(context)

    assert context.data["level_up_hand"] == PokerHand.PAIR


def test_certificate_joker():

    joker = CertificateJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2)
    )

    joker.apply(context)

    assert len(context.data["created_cards"]) == 1


def test_cartomancer_joker():

    joker = CartomancerJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="BLIND_SELECTED"
    )

    joker.apply(context)

    assert len(context.data["created_consumables"]) == 1


def test_dna_joker():

    joker = DNAJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    card = BalatroCard("A", "Hearts")

    context = JokerContext(
        state=state,
        trigger="HAND_SCORED",
        cards=[card]
    )

    joker.apply(context)

    assert context.data["copied_cards"] == [card]


def test_marble_joker():

    joker = MarbleJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="ROUND_STARTED"
    )

    joker.apply(context)

    assert len(context.data["created_cards"]) == 1
    assert context.data["created_cards"][0].enhancement == "Stone"


def test_seance_joker():

    joker = SeanceJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        poker_hand=PokerHand.STRAIGHT_FLUSH
    )

    joker.apply(context)

    assert len(context.data["created_consumables"]) == 1


def test_sixth_sense_joker():

    joker = SixthSenseJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    card = BalatroCard("6", "Hearts")

    context = JokerContext(
        state=state,
        trigger="HAND_SCORED",
        cards=[card]
    )

    joker.apply(context)

    assert context.data["destroyed_cards"] == [card]
    assert len(context.data["created_consumables"]) == 1


def test_trading_card_joker():

    joker = TradingCardJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    card = BalatroCard("A", "Hearts")

    context = JokerContext(
        state=state,
        trigger="CARDS_DISCARDED",
        cards=[card]
    )

    joker.apply(context)

    assert context.data["destroyed_cards"] == [card]
    assert context.data["money"] == 3


def test_vagabond_joker():

    joker = VagabondJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "money": 4
        }
    )()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2)
    )

    joker.apply(context)

    assert len(context.data["created_consumables"]) == 1


def test_eight_ball_joker(monkeypatch):

    monkeypatch.setattr(
        "games.balatro.jokers.eight_ball.random.random",
        lambda: 0.1
    )

    joker = EightBallJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="HAND_SCORED",
        cards=[BalatroCard("8", "Hearts")]
    )

    joker.apply(context)

    assert len(context.data["created_consumables"]) == 1


def test_eight_ball_joker_does_not_trigger_without_eight():

    monkeypatch = None

    joker = EightBallJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="HAND_SCORED",
        cards=[BalatroCard("7", "Hearts")]
    )

    joker.apply(context)

    assert "created_consumables" not in context.data


def test_scary_face_joker():

    joker = ScaryFaceJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        cards=[
            BalatroCard("K", "Hearts"),
            BalatroCard("Q", "Spades")
        ]
    )

    joker.apply(context)

    assert context.score.chips == 70


def test_smiley_face_joker():

    joker = SmileyFaceJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        cards=[
            BalatroCard("K", "Hearts"),
            BalatroCard("Q", "Spades")
        ]
    )

    joker.apply(context)

    assert context.score.mult == 12


def test_photograph_joker():

    joker = PhotographJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        cards=[
            BalatroCard("K", "Hearts"),
            BalatroCard("7", "Spades")
        ]
    )

    joker.apply(context)

    assert context.score.x_mult == 2


def test_photograph_joker_does_not_trigger_without_face_first():

    joker = PhotographJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        cards=[
            BalatroCard("7", "Hearts"),
            BalatroCard("K", "Spades")
        ]
    )

    joker.apply(context)

    assert context.score.x_mult == 1


def test_sock_and_buskin_joker():

    joker = SockAndBuskinJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        cards=[
            BalatroCard("K", "Hearts"),
            BalatroCard("7", "Spades"),
            BalatroCard("J", "Clubs")
        ]
    )

    joker.apply(context)

    assert context.data["retrigger_cards"] == 2


def test_hanging_chad_joker():

    joker = HangingChadJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        cards=[
            BalatroCard("A", "Hearts")
        ]
    )

    joker.apply(context)

    assert context.data["retrigger_first_card"] == 2


def test_four_fingers_joker():

    joker = FourFingersJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(state=state)

    joker.apply(context)

    assert context.data["four_fingers"] is True


def test_shortcut_joker():

    joker = ShortcutJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(state=state)

    joker.apply(context)

    assert context.data["shortcut"] is True


def test_runner_joker():

    joker = RunnerJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(30, 4),
        poker_hand=PokerHand.STRAIGHT
    )

    joker.apply(context)

    assert joker.chips == 15
    assert context.score.chips == 45


def test_runner_joker_only_triggers_on_straight():

    joker = RunnerJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        poker_hand=PokerHand.PAIR
    )

    joker.apply(context)

    assert joker.chips == 0
    assert context.score.chips == 10


def test_smeared_joker():

    joker = SmearedJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(state=state)

    joker.apply(context)

    assert context.data["smeared_suits"]["Hearts"] == "Red"
    assert context.data["smeared_suits"]["Diamonds"] == "Red"
    assert context.data["smeared_suits"]["Clubs"] == "Black"
    assert context.data["smeared_suits"]["Spades"] == "Black"


def test_flower_pot_joker():

    joker = FlowerPotJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        cards=[
            BalatroCard("A", "Hearts"),
            BalatroCard("K", "Diamonds"),
            BalatroCard("Q", "Clubs"),
            BalatroCard("J", "Spades"),
        ]
    )

    joker.apply(context)

    assert context.score.x_mult == 3


def test_flower_pot_joker_does_not_trigger_without_all_suits():

    joker = FlowerPotJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        cards=[
            BalatroCard("A", "Hearts"),
            BalatroCard("K", "Diamonds"),
            BalatroCard("Q", "Clubs"),
        ]
    )

    joker.apply(context)

    assert context.score.x_mult == 1


def test_wee_joker():

    joker = WeeJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        cards=[
            BalatroCard("2", "Hearts"),
            BalatroCard("2", "Spades"),
        ]
    )

    joker.apply(context)

    assert joker.chips == 16
    assert context.score.chips == 26


def test_midas_mask_joker():

    joker = MidasMaskJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    cards = [
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Spades"),
        BalatroCard("7", "Clubs"),
    ]

    context = JokerContext(
        state=state,
        cards=cards
    )

    joker.apply(context)

    assert cards[0].enhancement == "Gold"
    assert cards[1].enhancement == "Gold"
    assert cards[2].enhancement is None


def test_abstract_joker():

    joker = AbstractJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker, object(), object()]
        }
    )()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2)
    )

    joker.apply(context)

    assert context.score.mult == 11


def test_acrobat_joker():

    joker = AcrobatJoker()

    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        data={"hands_remaining": 0}
    )

    joker.apply(context)

    assert context.score.x_mult == 3


def test_delayed_gratification_joker():

    joker = DelayedGratificationJoker()

    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="ROUND_ENDED",
        data={"discards_remaining": 2}
    )

    joker.apply(context)

    assert context.data["delayed_gratification_money"] == 4


def test_to_do_list_joker(monkeypatch):

    monkeypatch.setattr(
        "games.balatro.jokers.to_do_list.random.choice",
        lambda values: PokerHand.PAIR
    )

    joker = ToDoListJoker()

    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="HAND_SCORED",
        poker_hand=PokerHand.PAIR
    )

    joker.apply(context)

    assert context.data["money"] == 4


def test_golden_joker():

    joker = GoldenJoker()

    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="ROUND_ENDED"
    )

    joker.apply(context)

    assert context.data["money"] == 4


def test_rocket_joker():

    joker = RocketJoker()

    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="ROUND_ENDED",
        data={"boss_blind": True}
    )

    joker.apply(context)

    assert context.data["money"] == 3


def test_cloud_9_joker():

    joker = Cloud9Joker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": [
                BalatroCard("A", "Hearts"),
                BalatroCard("K", "Spades")
            ]
        }
    )()

    context = JokerContext(
        state=state,
        trigger="ROUND_ENDED"
    )

    joker.apply(context)

    assert context.data["money"] == 2


def test_reserved_parking_joker(monkeypatch):

    monkeypatch.setattr(
        "games.balatro.jokers.reserved_parking.random.random",
        lambda: 0.1
    )

    joker = ReservedParkingJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker],
            "hand": [
                BalatroCard("K", "Hearts")
            ]
        }
    )()

    context = JokerContext(
        state=state,
        trigger="ROUND_ENDED"
    )

    joker.apply(context)

    assert context.data["money"] == 1


def test_egg_joker():

    joker = EggJoker()

    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="ROUND_ENDED"
    )

    joker.apply(context)

    assert joker.sell_value == 6


def test_gift_card_joker():

    joker = GiftCardJoker()

    card = BalatroCard("A", "Hearts")
    card.sell_value = 3

    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="ROUND_ENDED",
        data={"owned_cards": [card]}
    )

    joker.apply(context)

    assert card.sell_value == 4


def test_ancient_joker_selects_suit(monkeypatch):

    monkeypatch.setattr(
        "games.balatro.jokers.ancient_joker.random.choice",
        lambda suits: "Hearts"
    )

    joker = AncientJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="ROUND_STARTED"
    )

    joker.apply(context)

    assert joker.suit == "Hearts"


def test_ancient_joker():

    joker = AncientJoker()
    joker.suit = "Hearts"

    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        cards=[
            BalatroCard("A", "Hearts"),
            BalatroCard("K", "Hearts"),
            BalatroCard("7", "Spades"),
        ]
    )

    joker.apply(context)

    assert context.score.x_mult == 2.25


def test_ancient_joker_does_not_trigger_without_matching_suit():

    joker = AncientJoker()
    joker.suit = "Hearts"

    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        cards=[
            BalatroCard("A", "Spades"),
            BalatroCard("K", "Clubs"),
        ]
    )

    joker.apply(context)

    assert context.score.x_mult == 1.0


def test_blue_joker():

    joker = BlueJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        data={
            "deck": [
                BalatroCard("A", "Hearts"),
                BalatroCard("K", "Spades"),
            ]
        }
    )

    joker.apply(context)

    assert context.score.chips == 14


def test_golden_ticket():

    joker = GoldenTicketJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="CARDS_SCORED",
        cards=[
            BalatroCard("A", "Hearts", enhancement="Gold"),
            BalatroCard("K", "Spades"),
        ]
    )

    joker.apply(context)

    assert context.data["money"] == 4


def test_luchador():

    joker = LuchadorJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="BOSS_BLIND_DEFEATED"
    )

    joker.apply(context)

    assert context.data["boss_blind_disabled"] is True


def test_mr_bones():

    joker = MrBonesJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    context = JokerContext(
        state=state,
        trigger="RUN_FAILED",
        data={
            "score": 30,
            "required_score": 100,
        }
    )

    joker.apply(context)

    assert context.data["prevented_loss"] is True


def test_invisible_joker():

    joker = InvisibleJoker()
    state = type("TestState", (), {"jokers": [joker]})()

    for _ in range(2):
        context = JokerContext(
            state=state,
            trigger="ROUND_ENDED"
        )
        joker.apply(context)

    assert context.data["invisible_joker_trigger"] is True


def test_joker_stencil():

    joker = JokerStencil()

    other = object()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker, other]
        }
    )()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2),
        data={"joker_slots": 5}
    )

    joker.apply(context)

    assert context.score.x_mult == 3


def test_brainstorm():

    first = object()
    joker = BrainstormJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [first, joker]
        }
    )()

    context = JokerContext(state=state)

    joker.apply(context)

    assert context.data["copy_joker"] is first


def test_madness_joker(monkeypatch):

    target = object()

    monkeypatch.setattr(
        "games.balatro.jokers.madness.random.choice",
        lambda jokers: target
    )

    joker = MadnessJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker, target]
        }
    )()

    context = JokerContext(
        state=state,
        trigger="SMALL_BLIND_SELECTED"
    )

    joker.apply(context)

    assert joker.x_mult == 1.5
    assert context.data["destroy_joker"] is target


def test_madness_does_not_trigger_on_boss():

    joker = MadnessJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker]
        }
    )()

    context = JokerContext(
        state=state,
        trigger="BOSS_BLIND_SELECTED"
    )

    joker.apply(context)

    assert joker.x_mult == 1.0
    assert "destroy_joker" not in context.data


def test_mime_joker():

    joker = MimeJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker]
        }
    )()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2)
    )

    joker.apply(context)

    assert context.data["retrigger_held_abilities"] == 1


def test_satellite_joker():

    joker = SatelliteJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker]
        }
    )()

    context = JokerContext(
        state=state,
        trigger="ROUND_ENDED",
        data={
            "used_planets": [
                "Mercury",
                "Venus",
                "Earth",
            ]
        }
    )

    joker.apply(context)

    assert context.data["money"] == 3


def test_satellite_only_counts_unique_planets():

    joker = SatelliteJoker()

    state = type(
        "TestState",
        (),
        {
            "jokers": [joker]
        }
    )()

    context = JokerContext(
        state=state,
        trigger="ROUND_ENDED",
        data={
            "used_planets": [
                "Mercury",
                "Mercury",
                "Venus",
            ]
        }
    )

    joker.apply(context)

    assert context.data["money"] == 2


def test_swashbuckler_joker():

    joker = SwashbucklerJoker()

    first = type(
        "TestJoker",
        (),
        {
            "sell_value": 4
        }
    )()

    second = type(
        "TestJoker",
        (),
        {
            "sell_value": 7
        }
    )()

    state = type(
        "TestState",
        (),
        {
            "jokers": [first, joker, second]
        }
    )()

    context = JokerContext(
        state=state,
        score=HandScore(10, 2)
    )

    joker.apply(context)

    assert context.score.mult == 13


def test_burglar_joker():

    joker = BurglarJoker()
    context = JokerContext(
        state=GameState(),
        trigger="BLIND_SELECTED",
        data={"discards_remaining": 2}
    )

    joker.apply(context)

    assert context.data["hands_gained"] == 3
    assert context.data["discards_lost"] == 2


def test_coupon_tag_joker():

    joker = CouponTagJoker()
    context = JokerContext(
        state=GameState(),
        trigger="ROUND_STARTED"
    )

    joker.apply(context)

    assert context.data["shop_free"] is True


def test_diet_cola_joker():

    joker = DietColaJoker()
    context = JokerContext(
        state=GameState(),
        trigger="SOLD",
        data={"sold_joker": joker}
    )

    joker.apply(context)

    assert context.data["double_tag"] is True


def test_hallucination_joker(monkeypatch):

    monkeypatch.setattr(
        "games.balatro.jokers.hallucination.random.random",
        lambda: 0.1
    )

    joker = HallucinationJoker()
    context = JokerContext(
        state=GameState(),
        trigger="BOOSTER_OPENED"
    )

    joker.apply(context)

    assert len(context.data["created_tarot_cards"]) == 1


def test_hiker_joker():

    joker = HikerJoker()
    card = BalatroCard("A", "Hearts")

    context = JokerContext(
        state=GameState(),
        trigger="HAND_SCORED",
        cards=[card]
    )

    joker.apply(context)

    assert card.permanent_bonus == 5


def test_merry_andy_joker():

    joker = MerryAndyJoker()
    context = JokerContext(
        state=GameState(),
        trigger="JOKER_ACQUIRED"
    )

    joker.apply(context)

    assert context.data["hand_size"] == 3
    assert context.data["discards_per_round"] == 1


def test_showman_joker():

    joker = ShowmanJoker()
    context = JokerContext(state=GameState())

    joker.apply(context)

    assert context.data["allow_duplicates"] is True


def test_stone_joker():

    joker = StoneJoker()
    card = BalatroCard("A", "Hearts", enhancement="Stone")

    context = JokerContext(
        state=GameState(),
        score=HandScore(10, 2),
        cards=[card]
    )

    joker.apply(context)

    assert context.score.chips == 35


def test_turtle_bean_joker():

    joker = TurtleBeanJoker()
    context = JokerContext(
        state=GameState(),
        trigger="ROUND_STARTED"
    )

    joker.apply(context)

    assert joker.hand_size == 4
    assert context.data["hand_size_modifier"] == 4