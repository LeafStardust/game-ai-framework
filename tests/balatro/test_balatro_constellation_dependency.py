from types import SimpleNamespace

from games.balatro.constellation_strategy_rules import constellation_partner_tier
from games.balatro.strategy import GOLD, NEUTRAL, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import conditional_joker_relationship


class ConstellationJoker:
    pass


class AstronomerJoker:
    pass


class SatelliteJoker:
    pass


def _state(*jokers):
    return SimpleNamespace(jokers=list(jokers))


def test_constellation_has_no_standalone_static_planet_evidence():
    candidate = ConstellationJoker()
    for strategy_id in (
        "planet_constellation",
        "planet_satellite",
        "planet_constellation_satellite",
    ):
        assert (
            RUNTIME_UNIVERSAL_BALATRO_STRATEGIES[strategy_id].relationship_for(
                candidate,
                kind="JOKER",
            )
            == NEUTRAL
        )


def test_constellation_is_neutral_without_astronomer_or_satellite():
    state = _state()
    candidate = ConstellationJoker()

    assert constellation_partner_tier(state) == NEUTRAL
    assert (
        conditional_joker_relationship(state, "planet_constellation", candidate)
        == NEUTRAL
    )


def test_astronomer_makes_constellation_silver_support():
    state = _state(AstronomerJoker())
    candidate = ConstellationJoker()

    assert constellation_partner_tier(state) == SILVER
    assert (
        conditional_joker_relationship(state, "planet_constellation", candidate)
        == SILVER
    )


def test_satellite_makes_constellation_gold_pair_payoff():
    state = _state(SatelliteJoker())
    candidate = ConstellationJoker()

    assert constellation_partner_tier(state) == GOLD
    assert (
        conditional_joker_relationship(state, "planet_satellite", candidate)
        == GOLD
    )
