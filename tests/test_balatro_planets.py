from games.balatro.planets import create_planet, random_planet


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