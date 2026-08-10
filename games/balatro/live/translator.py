from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.interfaces import BalatroStateTranslator
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.state import BalatroState


class DefaultBalatroStateTranslator(BalatroStateTranslator):

    RANKS = {
        "Ace": "A",
        "King": "K",
        "Queen": "Q",
        "Jack": "J",
    }

    ENHANCEMENTS = {
        "m_bonus": "Bonus",
        "m_mult": "Mult",
        "m_wild": "Wild",
        "m_glass": "Glass",
        "m_steel": "Steel",
        "m_stone": "Stone",
        "m_gold": "Gold",
        "m_lucky": "Lucky",
    }

    EDITIONS = {
        "foil": "Foil",
        "holo": "Holographic",
        "holographic": "Holographic",
        "polychrome": "Polychrome",
        "negative": "Negative",
    }

    STAKES = {
        1: "WHITE",
        2: "RED",
        3: "GREEN",
        4: "BLACK",
        5: "BLUE",
        6: "PURPLE",
        7: "ORANGE",
        8: "GOLD",
    }

    def translate(
        self,
        snapshot: LiveBalatroSnapshot
    ) -> BalatroState:
        payload = snapshot.payload
        state = BalatroState()

        state.money = int(payload.get("money", 0))
        state.ante = int(payload.get("ante", 1))
        state.round = int(payload.get("round", 1))
        state.blind_score = int(payload.get("blind_score", 0))
        state.discards_remaining = int(payload.get("discards_left", 0))
        state.hand_size = int(payload.get("hand_size", len(payload.get("hand", []))))
        state.consumable_slots = int(payload.get("consumable_slots", 2))
        state.deck_name = str(payload.get("deck_name", "RED")).upper()
        state.stake_name = self._stake_name(payload)
        state.phase = snapshot.phase

        state.hand = self._cards(payload.get("hand", []))
        state.deck = self._cards(payload.get("deck", []))

        blind = payload.get("blind")
        if blind:
            blind_type = BlindType.BOSS if blind.get("boss") else BlindType.SMALL
            state.blind = Blind(
                blind_type,
                int(blind.get("chips", 0)),
            )
            state.boss_name = blind.get("name") if blind_type == BlindType.BOSS else None

        return state

    def _stake_name(self, payload: dict) -> str:
        if payload.get("stake_name"):
            return str(payload["stake_name"]).upper()

        stake = payload.get("stake")
        if stake is None:
            return "WHITE"

        return self.STAKES.get(int(stake), "WHITE")

    def _cards(self, cards: list[dict]) -> list[BalatroCard]:
        return [
            self._card(card)
            for card in cards
            if card.get("rank") and card.get("suit")
        ]

    def _card(self, card: dict) -> BalatroCard:
        rank = str(card["rank"])
        enhancement = card.get("enhancement")
        edition = card.get("edition")

        return BalatroCard(
            rank=self.RANKS.get(rank, rank),
            suit=str(card["suit"]),
            enhancement=self.ENHANCEMENTS.get(enhancement, enhancement),
            edition=self.EDITIONS.get(edition, edition),
            seal=card.get("seal"),
        )
