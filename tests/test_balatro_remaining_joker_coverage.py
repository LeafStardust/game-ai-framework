import games.balatro.jokers as joker_package

from games.balatro.build.effects import (
    CONSUMABLE_GENERATE,
    DECK_REMOVE,
    ECONOMY,
    HAND_LEVEL,
    SCORE_MULT,
    SCORE_XMULT,
)
from games.balatro.build.joker_coverage import (
    COVERED,
    ERROR,
    OPAQUE,
    PARAMETERIZED,
    PARTIAL,
    JokerCoverageAuditor,
)
from games.balatro.build.joker_scenarios import (
    BOSS_CONTROL,
    JOKER_COPY,
    JOKER_DESTROY,
    PLAYED_RETRIGGER,
    PROBABILITY_MULTIPLIER,
    ScenarioJokerBehaviorAnalyzer,
)
from games.balatro.build.joker_semantics import SELL_VALUE_GROWTH
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.dagger import DaggerJoker
from games.balatro.jokers.dusk import DuskJoker
from games.balatro.jokers.eight_ball import EightBallJoker
from games.balatro.jokers.gift_card import GiftCardJoker
from games.balatro.jokers.golden_ticket import GoldenTicketJoker
from games.balatro.jokers.invisible_joker import InvisibleJoker
from games.balatro.jokers.lucky_cat import LuckyCatJoker
from games.balatro.jokers.madness import MadnessJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.jokers.sixth_sense import SixthSenseJoker
from games.balatro.jokers.trading_card import TradingCardJoker


def _describe(joker):
    return ScenarioJokerBehaviorAnalyzer().describe(joker)


def test_remaining_contextual_joker_families_are_semantically_visible():
    burnt = _describe(BurntJoker())
    chicot = _describe(ChicotJoker())
    dagger = _describe(DaggerJoker())
    dusk = _describe(DuskJoker())
    eight_ball = _describe(EightBallJoker())
    gift_card = _describe(GiftCardJoker())
    golden_ticket = _describe(GoldenTicketJoker())
    invisible = _describe(InvisibleJoker())
    lucky_cat = _describe(LuckyCatJoker())
    madness = _describe(MadnessJoker())
    oops = _describe(OopsAll6sJoker())
    ride_the_bus = _describe(RideTheBusJoker())

    assert HAND_LEVEL in burnt.produces
    assert BOSS_CONTROL in chicot.produces
    assert SCORE_MULT in dagger.produces
    assert JOKER_DESTROY in dagger.penalizes
    assert PLAYED_RETRIGGER in dusk.produces
    assert CONSUMABLE_GENERATE in eight_ball.produces
    assert SELL_VALUE_GROWTH in gift_card.produces
    assert ECONOMY in golden_ticket.produces
    assert JOKER_COPY in invisible.produces
    assert SCORE_XMULT in lucky_cat.produces
    assert SCORE_XMULT in madness.produces
    assert JOKER_DESTROY in madness.penalizes
    assert PROBABILITY_MULTIPLIER in oops.produces
    assert SCORE_MULT in ride_the_bus.produces


def test_trigger_guard_flags_do_not_remain_unknown_semantic_outputs():
    sixth_sense = _describe(SixthSenseJoker())
    trading_card = _describe(TradingCardJoker())

    assert DECK_REMOVE in sixth_sense.produces
    assert CONSUMABLE_GENERATE in sixth_sense.produces
    assert "signal:sixth_sense_triggered" not in sixth_sense.produces

    assert DECK_REMOVE in trading_card.produces
    assert ECONOMY in trading_card.produces
    assert "signal:trading_card_triggered" not in trading_card.produces


def test_joker_discovery_does_not_require_package_file(monkeypatch):
    monkeypatch.setattr(joker_package, "__file__", None)

    classes = JokerCoverageAuditor._classes()

    assert len(classes) == 152


def test_every_repository_joker_has_semantic_coverage():
    report = JokerCoverageAuditor().audit()

    assert len(report.entries) == 152
    assert report.count(COVERED) == 152
    assert report.count(OPAQUE) == 0
    assert report.count(PARTIAL) == 0
    assert report.count(ERROR) == 0
    assert report.count(PARAMETERIZED) == 0
