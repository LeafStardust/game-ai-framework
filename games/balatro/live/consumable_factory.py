from games.balatro.planets import PLANET_CARDS, create_planet
from games.balatro.spectrals import SPECTRAL_CARDS, create_spectral
from games.balatro.tarots import TAROT_CARDS, create_tarot


class LiveConsumableFactory:

    def __init__(self):
        self.planet_names = {
            planet.name: key
            for key, planet in PLANET_CARDS.items()
        }

    def create(
        self,
        data: dict,
        live_id: int | str | None = None,
    ):
        name = (
            data.get("label")
            or data.get("ability_name")
            or self._name_from_key(data.get("key"))
        )

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

        consumable.live_id = (
            live_id
            if live_id is not None
            else data.get("id")
        )

        cost = data.get("cost") or {}
        if cost.get("buy") is not None:
            consumable.price = int(cost["buy"])

        return consumable

    @staticmethod
    def _name_from_key(key: str | None) -> str | None:
        if not key or not key.startswith("c_"):
            return None

        words = key[2:].replace("_", " ").title()

        if words == "Fool":
            return "The Fool"
        if words == "High Priestess":
            return "The High Priestess"
        if words == "Empress":
            return "The Empress"
        if words == "Emperor":
            return "The Emperor"
        if words == "Hierophant":
            return "The Hierophant"
        if words == "Lovers":
            return "The Lovers"
        if words == "Chariot":
            return "The Chariot"
        if words == "Hermit":
            return "The Hermit"
        if words == "Wheel Of Fortune":
            return "The Wheel of Fortune"
        if words == "Hanged Man":
            return "The Hanged Man"
        if words == "Devil":
            return "The Devil"
        if words == "Tower":
            return "The Tower"
        if words == "Star":
            return "The Star"
        if words == "Moon":
            return "The Moon"
        if words == "Sun":
            return "The Sun"
        if words == "World":
            return "The World"
        if words == "Soul":
            return "The Soul"

        return words
