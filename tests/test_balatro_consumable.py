import random

from games.balatro.consumable import (
    Consumable,
    ConsumableContext,
    PlanetCard
)
from games.balatro.state import BalatroState
from games.balatro.planets import PLANET_CARDS, create_planet, random_planet


class TestConsumable(Consumable):

    name = "Test Consumable"
    category = "TEST"

    def can_use(self, context):
        return True

    def use(self, context):
        context.state.money += 10
        return context


def test_consumable_context_creation():

    state = BalatroState()
    context = ConsumableContext(state=state)

    assert context.state is state
    assert context.cards == []
    assert context.target is None
    assert context.data == {}


def test_consumable_usage():

    state = BalatroState()
    consumable = TestConsumable()
    context = ConsumableContext(state=state)

    assert consumable.name == "Test Consumable"
    assert consumable.category == "TEST"
    assert consumable.can_use(context)

    consumable.use(context)

    assert state.money == 10


def test_planet_card_metadata():

    planet = PLANET_CARDS["MERCURY"]

    assert planet.name == "Mercury"
    assert planet.category == "PLANET"
    assert planet.hand_type == "PAIR"
    assert planet.chips == 15
    assert planet.mult == 1


def test_planet_card_can_use():

    state = BalatroState()

    planet = PLANET_CARDS["MERCURY"]

    assert planet.can_use(
        ConsumableContext(state)
    )


def test_planet_card_increases_hand_level():

    state = BalatroState()

    planet = PLANET_CARDS["MERCURY"]

    planet.use(
        ConsumableContext(state)
    )

    assert state.hand_levels["PAIR"] == 2


def test_planet_card_use_returns_effect_data():

    state = BalatroState()

    planet = PLANET_CARDS["MERCURY"]

    context = planet.use(
        ConsumableContext(state)
    )

    assert context.data["chips"] == 15
    assert context.data["mult"] == 1


def test_create_planet_returns_independent_instance():

    first = create_planet("MERCURY")
    second = create_planet("MERCURY")

    assert first is not second
    assert first.name == second.name
    assert first.hand_type == second.hand_type
    assert first.chips == second.chips
    assert first.mult == second.mult


def test_random_planet_returns_valid_planet():

    planet = random_planet(random.Random())

    assert planet.category == "PLANET"
    assert planet.name in [
        planet.name
        for planet in PLANET_CARDS.values()
    ]


def test_consumable_has_default_price():

    consumable = create_planet("MERCURY")

    assert consumable.price == 3