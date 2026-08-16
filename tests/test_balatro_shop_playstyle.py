from types import SimpleNamespace

from games.balatro.actions import BUY_CONSUMABLE, BalatroAction
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.card import BalatroCard
from games.balatro.joker import (
    Joker,
    JokerContext,
    Playstyle,
    PlaystyleAffinity,
)
from games.balatro.planets import create_planet
from games.balatro.shop_playstyle import BuildAwareShopItemValueEstimator
from games.balatro.state import BalatroState


class _PairAlignedJoker(Joker):
    playstyle_affinities = {
        Playstyle.PAIR: PlaystyleAffinity.POSITIVE,
        Playstyle.FLUSH: PlaystyleAffinity.NEGATIVE,
    }

    def apply(self, context: JokerContext) -> JokerContext:
        return context


class _FlushAlignedJoker(Joker):
    playstyle_affinities = {
        Playstyle.FLUSH: PlaystyleAffinity.POSITIVE,
        Playstyle.PAIR: PlaystyleAffinity.NEGATIVE,
    }

    def apply(self, context: JokerContext) -> JokerContext:
        return context


class _NoConsumableBuildPath:
    def evaluate(self, consumable, state):
        del consumable, state
        return SimpleNamespace(
            build_path_gain=0.0,
            paths=(),
            contributions=(),
        )


class _EqualPlanetOutlook:
    def evaluate(self, state, planet):
        del state, planet
        return SimpleNamespace(
            expected_future_frequency=0.5,
            structural_feasibility=0.5,
            observed_plays=1,
            total_observed_plays=2,
            marginal_level_gain=1.0,
            future_value=0.5,
            speculative=False,
        )


def _standard_deck():
    ranks = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    suits = ("Hearts", "Diamonds", "Clubs", "Spades")
    return [BalatroCard(rank, suit) for suit in suits for rank in ranks]


def _state(*, ante: int, joker: Joker) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = ante
    state.money = 20
    state.jokers = [joker]
    state.hand_levels["PAIR"] = 1
    state.hand_levels["FLUSH"] = 1
    return state


def _estimator(*, real_outlook: bool = False) -> BuildAwareShopItemValueEstimator:
    kwargs = {}
    if not real_outlook:
        kwargs["planet_outlook"] = _EqualPlanetOutlook()
    return BuildAwareShopItemValueEstimator(
        joker_build_value=JokerBuildValueEvaluator(),
        consumable_build=_NoConsumableBuildPath(),
        **kwargs,
    )


def _planet_values(estimator, state):
    mercury = create_planet("MERCURY")
    jupiter = create_planet("JUPITER")
    pair_value, pair_notes = estimator.estimate(
        state,
        BalatroAction(BUY_CONSUMABLE, target=mercury),
    )
    flush_value, flush_notes = estimator.estimate(
        state,
        BalatroAction(BUY_CONSUMABLE, target=jupiter),
    )
    return pair_value, pair_notes, flush_value, flush_notes


def test_d14_planet_value_prefers_synergy_and_penalizes_anti_synergy():
    estimator = _estimator()
    state = _state(ante=4, joker=_PairAlignedJoker())

    pair_value, pair_notes, flush_value, flush_notes = _planet_values(
        estimator,
        state,
    )

    assert pair_value > flush_value
    assert any("fit=1.000" in note for note in pair_notes)
    assert any("fit=-1.000" in note for note in flush_notes)
    assert any("mode=PIVOTABLE" in note for note in pair_notes)


def test_d14_uses_locked_intent_after_owned_build_flips_direction():
    estimator = _estimator()
    state = _state(ante=4, joker=_PairAlignedJoker())

    _planet_values(estimator, state)
    state.ante = 5
    locked_pair, locked_notes, locked_flush, _ = _planet_values(estimator, state)
    assert locked_pair > locked_flush
    assert any("mode=LOCKED" in note for note in locked_notes)

    state.ante = 6
    state.jokers = [_FlushAlignedJoker()]
    later_pair, later_notes, later_flush, later_flush_notes = _planet_values(
        estimator,
        state,
    )

    assert later_pair > later_flush
    assert any("fit=1.000" in note for note in later_notes)
    assert any("fit=-1.000" in note for note in later_flush_notes)
    assert any("mode=LOCKED" in note for note in later_notes)


def test_d14_standard_deck_rejects_raw_neptune_level_gain_as_strategy():
    estimator = _estimator(real_outlook=True)
    state = _state(ante=1, joker=_PairAlignedJoker())
    state.jokers = []
    state.owned_deck = _standard_deck()
    state.hand_size = 8

    mercury_value, mercury_notes = estimator.estimate(
        state,
        BalatroAction(BUY_CONSUMABLE, target=create_planet("MERCURY")),
    )
    neptune_value, neptune_notes = estimator.estimate(
        state,
        BalatroAction(BUY_CONSUMABLE, target=create_planet("NEPTUNE")),
    )

    assert mercury_value > neptune_value
    assert any("Planet speculative=True" in note for note in neptune_notes)
    assert any("Planet structural feasibility=" in note for note in mercury_notes)
