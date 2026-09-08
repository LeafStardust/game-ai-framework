from types import SimpleNamespace

from games.balatro.actions import BUY_VOUCHER, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.live.planet_policy import HOLD, LivePlanetPolicy
from games.balatro.planets import create_planet
from games.balatro.scoring import BalatroScorer
from games.balatro.shop_policy import DefaultShopItemValueEstimator
from games.balatro.state import BalatroState


class PerkeoJoker:
    name = "Perkeo"


def _flush_cards():
    return [BalatroCard(rank, "Hearts") for rank in ("2", "4", "7", "9", "K")]


def test_observatory_applies_x15_for_one_matching_held_planet() -> None:
    scorer = BalatroScorer()
    state = BalatroState()
    state.vouchers = ["Observatory"]
    state.consumables = [create_planet("JUPITER")]
    baseline = BalatroState()
    normal = scorer.score(PokerHand.FLUSH, baseline).total
    observed = scorer.score(PokerHand.FLUSH, state).total
    assert observed == int(normal * 1.5)


def test_observatory_matching_planets_stack_multiplicatively() -> None:
    scorer = BalatroScorer()
    state = BalatroState()
    state.vouchers = ["Observatory"]
    state.consumables = [create_planet("JUPITER"), create_planet("JUPITER")]
    baseline = BalatroState()
    normal = scorer.score(PokerHand.FLUSH, baseline).total
    observed = scorer.score(PokerHand.FLUSH, state).total
    assert observed == int(normal * 2.25)


def test_observatory_ignores_nonmatching_held_planets() -> None:
    scorer = BalatroScorer()
    state = BalatroState()
    state.vouchers = ["Observatory"]
    state.consumables = [create_planet("SATURN")]
    baseline = BalatroState()
    assert scorer.score(PokerHand.FLUSH, state).total == scorer.score(PokerHand.FLUSH, baseline).total


def test_d7_preserves_observatory_planet_without_survival_gain() -> None:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.vouchers = ["Observatory"]
    planet = create_planet("JUPITER")
    state.consumables = [planet]
    state.consumable_slots = 1
    state.hand = _flush_cards()
    state.hands_remaining = 4
    state.blind = SimpleNamespace(requirement=100)
    decision = LivePlanetPolicy().recommend(state, planet)
    assert decision.decision == HOLD
    assert any("Observatory" in reason for reason in decision.rationale)


def test_observatory_voucher_value_rises_with_planet_and_perkeo_infrastructure() -> None:
    estimator = DefaultShopItemValueEstimator()
    candidate = SimpleNamespace(label="Observatory", price=10)
    plain = BalatroState()
    plain.phase = "SHOP"
    plain_value, _ = estimator.estimate(plain, BalatroAction(BUY_VOUCHER, target=candidate))
    developed = BalatroState()
    developed.phase = "SHOP"
    developed.consumables = [create_planet("JUPITER")]
    developed.jokers = [PerkeoJoker()]
    developed_value, notes = estimator.estimate(developed, BalatroAction(BUY_VOUCHER, target=candidate))
    assert developed_value > plain_value
    assert any("Perkeo" in note for note in notes)
