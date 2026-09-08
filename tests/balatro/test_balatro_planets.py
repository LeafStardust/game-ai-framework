from games.balatro.planets import create_planet, random_planet
from games.balatro.consumable import ConsumableContext
from games.balatro.state import BalatroState


def test_create_planet_returns_independent_instance():

    planet = create_planet(
        "PLUTO"
    )

    assert planet.name == "Pluto"
    assert planet.hand_type == "HIGH_CARD"

    other = create_planet(
        "PLUTO"
    )

    assert planet is not other


def test_random_planet_uses_rng():

    class TestRng:

        def choice(self, values):
            return "PLUTO"

    planet = random_planet(
        TestRng()
    )

    assert planet.name == "Pluto"


def test_planet_can_use_without_cards():

    state = BalatroState()

    planet = create_planet(
        "PLUTO"
    )

    context = ConsumableContext(
        state=state
    )

    assert planet.can_use(context)


def test_planet_use_levels_up_hand():

    state = BalatroState()

    planet = create_planet(
        "PLUTO"
    )

    context = ConsumableContext(
        state=state
    )

    planet.use(context)

    assert state.hand_levels["HIGH_CARD"] == 2