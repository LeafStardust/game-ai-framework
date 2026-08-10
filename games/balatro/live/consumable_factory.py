from games.balatro.planets import PLANET_CARDS, create_planet
from games.balatro.spectrals import SPECTRAL_CARDS, create_spectral
from games.balatro.tarots import TAROT_CARDS, create_tarot


class LiveConsumableFactory:

    def __init__(self):
        self.planet_names = {
            planet.name: key
            for key, planet in PLANET_CARDS.items()
        }

    def create(self, data: dict):
        name = data.get("ability_name")
        if not name:
            return None

        if name in TAROT_CARDS:
            consumable = create_tarot(name)
        elif name in SPECTRAL_CARDS:
            consumable = create_spectral(name)
        elif name in self.planet_names:
            consumable = create_planet(
                self.planet_names[name]
            )
        else:
            return None

        consumable.live_id = data.get("id")
        return consumable
