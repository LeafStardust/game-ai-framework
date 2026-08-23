from types import SimpleNamespace

from games.balatro.bonds.evaluation import EVALUATORS
from games.balatro.consumable import PlanetCard
from games.balatro.shop_consumable_policy import HOLD, ConsumableAcquisitionPolicy
from games.balatro.state import BalatroState


class _Joker:
    def __init__(self, name: str):
        self.name = name


def _face_state(*names: str):
    state = BalatroState()
    state.jokers = [_Joker(name) for name in names]
    state.owned_deck = list(state.deck)
    return state


def test_pareidolia_plus_scary_face_gets_semantic_enabler_bridge():
    development = EVALUATORS["face_cards"](_face_state("Pareidolia", "Scary Face"))

    sources = {part.source for part in development.contributions}
    assert "Pareidolia all-card face enabler bridge" in sources
    assert development.contribution >= 14.0


def test_pareidolia_without_face_payoff_gets_no_bridge():
    development = EVALUATORS["face_cards"](_face_state("Pareidolia"))

    sources = {part.source for part in development.contributions}
    assert "Pareidolia all-card face enabler bridge" not in sources


def test_d4_rejects_neptune_for_unplayed_level_one_straight_flush():
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.hand_levels["STRAIGHT_FLUSH"] = 1
    state.hand_play_counts["STRAIGHT_FLUSH"] = 0
    neptune = PlanetCard("Neptune", "STRAIGHT_FLUSH", 40, 4)

    decision = ConsumableAcquisitionPolicy().decide(state, neptune)

    assert decision.action == HOLD
    assert decision.selected is None
    assert any("zero play history" in note for note in decision.rationale)


def test_planet_relevance_guard_does_not_override_existing_hold():
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 0
    state.hand_levels["PAIR"] = 3
    state.hand_play_counts["PAIR"] = 4
    mercury = PlanetCard("Mercury", "PAIR", 15, 1)
    mercury.price = 99

    decision = ConsumableAcquisitionPolicy().decide(state, mercury)

    assert decision.action == HOLD
