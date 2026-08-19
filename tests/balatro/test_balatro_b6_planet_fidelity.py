from games.balatro.live.consumable_factory import LiveConsumableFactory
from games.balatro.planets import (
    BASE_PLANET_NAMES,
    PLANET_CARDS,
    SECRET_PLANET_NAMES,
    eligible_planet_names,
    random_planet,
)
from games.balatro.state import BalatroState


def test_base_planet_hand_mappings_match_vanilla():
    jupiter = PLANET_CARDS["JUPITER"]
    saturn = PLANET_CARDS["SATURN"]
    neptune = PLANET_CARDS["NEPTUNE"]

    assert (jupiter.hand_type, jupiter.chips, jupiter.mult) == ("FLUSH", 15, 2)
    assert (saturn.hand_type, saturn.chips, saturn.mult) == ("STRAIGHT", 30, 3)
    assert (neptune.hand_type, neptune.chips, neptune.mult) == (
        "STRAIGHT_FLUSH",
        40,
        4,
    )


def test_secret_planet_definitions_match_vanilla_level_gains():
    assert (
        PLANET_CARDS["PLANET_X"].name,
        PLANET_CARDS["PLANET_X"].hand_type,
        PLANET_CARDS["PLANET_X"].chips,
        PLANET_CARDS["PLANET_X"].mult,
    ) == ("Planet X", "FIVE_OF_A_KIND", 35, 3)
    assert (
        PLANET_CARDS["CERES"].name,
        PLANET_CARDS["CERES"].hand_type,
        PLANET_CARDS["CERES"].chips,
        PLANET_CARDS["CERES"].mult,
    ) == ("Ceres", "FLUSH_HOUSE", 40, 4)
    assert (
        PLANET_CARDS["ERIS"].name,
        PLANET_CARDS["ERIS"].hand_type,
        PLANET_CARDS["ERIS"].chips,
        PLANET_CARDS["ERIS"].mult,
    ) == ("Eris", "FLUSH_FIVE", 50, 3)


def test_secret_planets_are_softlocked_until_corresponding_hand_was_played():
    state = BalatroState()

    assert eligible_planet_names(state) == tuple(BASE_PLANET_NAMES)

    state.hand_play_counts["FIVE_OF_A_KIND"] = 1
    assert eligible_planet_names(state) == (*BASE_PLANET_NAMES, "PLANET_X")

    state.hand_play_counts["FLUSH_HOUSE"] = 2
    state.hand_play_counts["FLUSH_FIVE"] = 1
    assert eligible_planet_names(state) == (
        *BASE_PLANET_NAMES,
        "PLANET_X",
        "CERES",
        "ERIS",
    )


def test_live_consumable_factory_resolves_secret_planet_center_keys():
    factory = LiveConsumableFactory()

    assert factory.create({"key": "c_planet_x"}).name == "Planet X"
    assert factory.create({"key": "c_ceres"}).name == "Ceres"
    assert factory.create({"key": "c_eris"}).name == "Eris"


class _ChoiceRecorder:
    def __init__(self):
        self.population = None

    def choice(self, population):
        self.population = tuple(population)
        return population[0]


def test_legacy_random_planet_defaults_to_base_pool_not_softlocked_planets():
    rng = _ChoiceRecorder()

    random_planet(rng)

    assert rng.population == tuple(BASE_PLANET_NAMES)
    assert set(rng.population).isdisjoint(SECRET_PLANET_NAMES)
