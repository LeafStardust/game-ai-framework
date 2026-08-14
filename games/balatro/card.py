from dataclasses import dataclass


ENHANCEMENTS = {
    "Bonus",
    "Mult",
    "Wild",
    "Glass",
    "Steel",
    "Stone",
    "Gold",
    "Lucky",
}

EDITIONS = {
    "Foil",
    "Holographic",
    "Polychrome",
    "Negative",
}

SEALS = {
    "Gold",
    "Red",
    "Blue",
    "Purple",
}


@dataclass
class BalatroCard:
    rank: str
    suit: str
    enhancement: str | None = None
    edition: str | None = None
    seal: str | None = None
    live_id: int | str | None = None
    # Public live-state flag set by Balatro when the card is currently debuffed.
    # The card keeps its rank/suit for poker-hand structure, but scoring/held-card
    # effects must treat a debuffed card as disabled.
    debuffed: bool = False

    @property
    def is_wild(self) -> bool:
        return self.enhancement == "Wild"

    @property
    def is_stone(self) -> bool:
        return self.enhancement == "Stone"

    @property
    def is_glass(self) -> bool:
        return self.enhancement == "Glass"

    @property
    def is_steel(self) -> bool:
        return self.enhancement == "Steel"

    def matches_suit(self, suit: str) -> bool:
        return (
            not self.is_stone
            and (
                self.suit == suit
                or self.is_wild
            )
        )

    def has_rank(self, rank: str) -> bool:
        return (
            not self.is_stone
            and self.rank == rank
        )
