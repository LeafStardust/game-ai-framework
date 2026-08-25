from types import SimpleNamespace

from games.balatro.jokers.constellation import ConstellationJoker
from games.balatro.live.consumable_timing import LiveConsumableTimingPolicy
from games.balatro.live.consumable_timing_core import USE
from games.balatro.planet_scaler_authority import has_planet_use_scaler
from games.balatro.planets import create_planet
from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy
from games.balatro.shop_consumable_policy import BUY_AND_USE, ConsumableAcquisitionPolicy
from games.balatro.state import BalatroState


def _state(*, money=20, phase="SHOP") -> BalatroState:
    state = BalatroState()
    state.phase = phase
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.money = money
    state.ante = 3
    state.jokers = [ConstellationJoker()]
    state.consumables = []
    state.consumable_slots = 2
    state.hand_levels = {
        "PAIR": 1,
        "THREE_OF_A_KIND": 1,
        "FULL_HOUSE": 1,
        "FOUR_OF_A_KIND": 1,
        "FLUSH": 1,
        "STRAIGHT": 1,
        "TWO_PAIR": 1,
        "STRAIGHT_FLUSH": 1,
        "HIGH_CARD": 1,
        "FIVE_OF_A_KIND": 1,
        "FLUSH_HOUSE": 1,
        "FLUSH_FIVE": 1,
    }
    state.hand_play_counts = {}
    return state


def test_constellation_is_canonical_planet_use_scaler():
    assert has_planet_use_scaler(_state())


def test_constellation_makes_celestial_need_maximal_even_without_hand_specialization():
    state = _state()
    profile = SimpleNamespace(hand_levels=tuple(state.hand_levels.items()))
    need, notes = BuildAwareShopBoosterPolicy()._build_need(
        state,
        profile,
        family="CELESTIAL",
    )

    assert need == 1.0
    assert any("Planet-use scaler active" in note for note in notes)


def test_constellation_buys_and_uses_off_path_planet_when_reserve_is_safe():
    state = _state(money=20)
    planet = create_planet("NEPTUNE")

    decision = ConsumableAcquisitionPolicy().decide(state, planet)

    assert decision.action == BUY_AND_USE
    assert decision.selected is not None
    assert decision.selected.economics.money_after >= decision.thresholds.reserve_target
    assert any("Planet-use scaler authority" in note for note in decision.rationale)


def test_constellation_uses_held_planet_instead_of_hoarding_it():
    state = _state(money=20)
    planet = create_planet("NEPTUNE")
    state.consumables = [planet]

    recommendation = LiveConsumableTimingPolicy().recommend(state, planet)

    assert recommendation.decision == USE
    assert any("Planet-use scaler" in note for note in recommendation.rationale)
