from games.balatro.consumable import PlanetCard


PLANET_CARDS = {
    "MERCURY": PlanetCard(
        "Mercury",
        "PAIR",
        15,
        1,
    ),
    "VENUS": PlanetCard(
        "Venus",
        "THREE_OF_A_KIND",
        20,
        2,
    ),
    "EARTH": PlanetCard(
        "Earth",
        "FULL_HOUSE",
        25,
        2,
    ),
    "MARS": PlanetCard(
        "Mars",
        "FOUR_OF_A_KIND",
        30,
        3,
    ),
    "JUPITER": PlanetCard(
        "Jupiter",
        "FLUSH",
        15,
        2,
    ),
    "SATURN": PlanetCard(
        "Saturn",
        "STRAIGHT",
        30,
        3,
    ),
    "URANUS": PlanetCard(
        "Uranus",
        "TWO_PAIR",
        20,
        1,
    ),
    "NEPTUNE": PlanetCard(
        "Neptune",
        "STRAIGHT_FLUSH",
        40,
        4,
    ),
    "PLUTO": PlanetCard(
        "Pluto",
        "HIGH_CARD",
        10,
        1,
    ),
    "PLANET_X": PlanetCard(
        "Planet X",
        "FIVE_OF_A_KIND",
        35,
        3,
    ),
    "CERES": PlanetCard(
        "Ceres",
        "FLUSH_HOUSE",
        40,
        4,
    ),
    "ERIS": PlanetCard(
        "Eris",
        "FLUSH_FIVE",
        50,
        3,
    ),
}

BASE_PLANET_NAMES = (
    "MERCURY",
    "VENUS",
    "EARTH",
    "MARS",
    "JUPITER",
    "SATURN",
    "URANUS",
    "NEPTUNE",
    "PLUTO",
)

SECRET_PLANET_NAMES = (
    "PLANET_X",
    "CERES",
    "ERIS",
)

SECRET_PLANET_UNLOCK_HANDS = {
    "PLANET_X": "FIVE_OF_A_KIND",
    "CERES": "FLUSH_HOUSE",
    "ERIS": "FLUSH_FIVE",
}

PLANET_NAMES = list(PLANET_CARDS.keys())


def create_planet(name: str):
    planet = PLANET_CARDS[name]

    return PlanetCard(
        planet.name,
        planet.hand_type,
        planet.chips,
        planet.mult,
    )


def eligible_planet_names(state=None) -> tuple[str, ...]:
    """Return the public vanilla Planet pool for the current run.

    The base nine are always eligible. Planet X, Ceres, and Eris are softlocked
    until their corresponding secret poker hand has been played at least once.
    Only public hand-play counts are consulted; no RNG or future pool draw is read.
    """
    names = list(BASE_PLANET_NAMES)
    if state is None:
        return tuple(names)

    play_counts = getattr(state, "hand_play_counts", {}) or {}
    for planet_name in SECRET_PLANET_NAMES:
        hand_type = SECRET_PLANET_UNLOCK_HANDS[planet_name]
        if int(play_counts.get(hand_type, 0) or 0) > 0:
            names.append(planet_name)
    return tuple(names)


def random_planet(rng):
    # Legacy offline callers have no run state, so preserve the always-eligible
    # base pool rather than silently sampling softlocked secret Planets.
    return create_planet(
        rng.choice(BASE_PLANET_NAMES)
    )
