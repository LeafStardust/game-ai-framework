from __future__ import annotations

from types import SimpleNamespace

import games.balatro  # install final package-level authorities
from games.balatro.actions import BUY_BOOSTER, BalatroAction
from games.balatro.live.shop import LiveShopItem
from games.balatro.live_joker_order_authority import _identity_xmult_factor
from games.balatro.live_decision_quality_policy import _strict_planet_hand_relevant
from games.balatro.planets import PLANET_CARDS
from games.balatro.shop_booster_policy import BUY, BuildAwareShopBoosterPolicy
from games.balatro.state import BalatroState


def _planet(name: str):
    return next(card for card in PLANET_CARDS.values() if card.name == name)


def _state() -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 0
    state.ante = 3
    state.joker_slots = 5
    state.jokers = []
    state.owned_deck = []
    state.hand_levels = {}
    state.hand_play_counts = {}
    return state


def _free_booster(label: str, center: str | None = None) -> BalatroAction:
    return BalatroAction(
        BUY_BOOSTER,
        target=LiveShopItem(
            kind="BOOSTER",
            label=label,
            price=0,
            area_index=0,
            center=center,
        ),
    )


def test_polychrome_edition_is_treated_as_xmult_for_ordering() -> None:
    joker = SimpleNamespace(name="Jolly Joker", edition="POLYCHROME")
    assert _identity_xmult_factor(joker) == 1.5


def test_one_accidental_straight_flush_does_not_make_neptune_relevant() -> None:
    state = BalatroState()
    state.hand_play_counts = {"STRAIGHT_FLUSH": 1, "PAIR": 8, "TWO_PAIR": 6}
    state.hand_levels = {"STRAIGHT_FLUSH": 2, "PAIR": 3, "TWO_PAIR": 3}
    state.jokers = []
    relevant, notes = _strict_planet_hand_relevant(state, _planet("Neptune"))
    assert not relevant
    assert any("off-plan/weak-history" in note for note in notes)


def test_sustained_primary_hand_can_still_make_planet_relevant() -> None:
    state = BalatroState()
    state.hand_play_counts = {"PAIR": 6, "TWO_PAIR": 2}
    state.hand_levels = {"PAIR": 2}
    state.jokers = []
    relevant, _ = _strict_planet_hand_relevant(state, _planet("Mercury"))
    assert relevant


def test_zero_cost_safe_booster_is_opened() -> None:
    result = BuildAwareShopBoosterPolicy().recommend(
        _state(),
        _free_booster("Standard Pack", "p_standard_normal_1"),
    )
    assert result.decision == BUY
    assert any("FREE BOOSTER AUTHORITY" in note for note in result.rationale)


def test_zero_cost_arcana_booster_uses_supported_pack_authority() -> None:
    result = BuildAwareShopBoosterPolicy().recommend(
        _state(),
        _free_booster("Arcana Pack", "p_arcana_normal_1"),
    )
    assert result.decision == BUY
    assert any("FREE BOOSTER AUTHORITY" in note for note in result.rationale)
