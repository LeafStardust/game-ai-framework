from __future__ import annotations

from games.balatro import strategy_conditional_relationships as relationships
from games.balatro.strategy import GOLD, NEUTRAL, SILVER
from games.balatro.state import BalatroState


class BullJoker:
    pass


class BootstrapsJoker:
    pass


class RocketJoker:
    pass


class ToTheMoonJoker:
    pass


class Cloud9Joker:
    pass


class SatelliteJoker:
    pass


class ReservedParkingJoker:
    pass


class BusinessCardJoker:
    pass


class FacelessJoker:
    pass


class MailInRebateJoker:
    pass


class DelayedGratificationJoker:
    pass


class GoldenJoker:
    pass


class GoldenTicketJoker:
    pass


class RoughGemJoker:
    pass


class PareidoliaJoker:
    pass


class PhotographJoker:
    pass


class TribouletJoker:
    pass


def _state(*jokers) -> BalatroState:
    state = BalatroState()
    state.jokers = list(jokers)
    return state


def test_cash_generators_are_neutral_without_bull_or_bootstraps() -> None:
    state = _state(RocketJoker(), Cloud9Joker())
    assert relationships.conditional_joker_relationship(
        state, "cash_bull_bootstraps", state.jokers[0]
    ) == NEUTRAL
    assert relationships.conditional_joker_relationship(
        state, "cash_bull_bootstraps", state.jokers[1]
    ) == NEUTRAL


def test_bull_activates_broad_cash_generation_support() -> None:
    support = [
        RocketJoker(),
        Cloud9Joker(),
        SatelliteJoker(),
        ReservedParkingJoker(),
        BusinessCardJoker(),
        FacelessJoker(),
        MailInRebateJoker(),
        DelayedGratificationJoker(),
        GoldenJoker(),
        GoldenTicketJoker(),
        RoughGemJoker(),
    ]
    state = _state(BullJoker(), *support)
    for joker in support:
        assert relationships.conditional_joker_relationship(
            state, "cash_bull_bootstraps", joker
        ) == SILVER


def test_rocket_to_the_moon_pair_is_gold_support_once_cash_scorer_exists() -> None:
    rocket = RocketJoker()
    moon = ToTheMoonJoker()
    state = _state(BootstrapsJoker(), rocket, moon)
    assert relationships.conditional_joker_relationship(
        state, "cash_bull_bootstraps", rocket
    ) == GOLD
    assert relationships.conditional_joker_relationship(
        state, "cash_bull_bootstraps", moon
    ) == GOLD


def test_pareidolia_is_gold_generic_face_route_activator() -> None:
    pareidolia = PareidoliaJoker()
    state = _state(pareidolia)
    assert relationships.conditional_joker_relationship(
        state, "face_cards", pareidolia
    ) == GOLD


def test_pareidolia_only_activates_specialized_face_routes_with_payoff_core() -> None:
    pareidolia = PareidoliaJoker()
    assert relationships.conditional_joker_relationship(
        _state(pareidolia), "face_photochad", pareidolia
    ) == NEUTRAL
    assert relationships.conditional_joker_relationship(
        _state(pareidolia), "face_triboulet_sock", pareidolia
    ) == NEUTRAL

    assert relationships.conditional_joker_relationship(
        _state(PhotographJoker(), pareidolia), "face_photochad", pareidolia
    ) == GOLD
    assert relationships.conditional_joker_relationship(
        _state(TribouletJoker(), pareidolia), "face_triboulet_sock", pareidolia
    ) == GOLD
