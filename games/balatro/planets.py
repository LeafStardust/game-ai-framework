from games.balatro.consumable import PlanetCard


PLANET_CARDS = {
    "MERCURY": PlanetCard(
        "Mercury",
        "PAIR",
        15,
        1
    ),
    "VENUS": PlanetCard(
        "Venus",
        "THREE_OF_A_KIND",
        20,
        2
    ),
    "EARTH": PlanetCard(
        "Earth",
        "FULL_HOUSE",
        25,
        2
    ),
    "MARS": PlanetCard(
        "Mars",
        "FOUR_OF_A_KIND",
        30,
        3
    ),
    "JUPITER": PlanetCard(
        "Jupiter",
        "STRAIGHT",
        15,
        2
    ),
    "SATURN": PlanetCard(
        "Saturn",
        "STRAIGHT_FLUSH",
        30,
        3
    ),
    "URANUS": PlanetCard(
        "Uranus",
        "TWO_PAIR",
        20,
        1
    ),
    "NEPTUNE": PlanetCard(
        "Neptune",
        "FLUSH",
        15,
        2
    ),
    "PLUTO": PlanetCard(
        "Pluto",
        "HIGH_CARD",
        10,
        1
    )
}


def create_planet(name: str):
    planet = PLANET_CARDS[name]

    return PlanetCard(
        planet.name,
        planet.hand_type,
        planet.chips,
        planet.mult
    )