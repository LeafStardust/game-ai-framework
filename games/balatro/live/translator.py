from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.consumable_factory import LiveConsumableFactory
from games.balatro.live.interfaces import BalatroStateTranslator
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.shop import LiveShopItemFactory
from games.balatro.state import BalatroState


class DefaultBalatroStateTranslator(BalatroStateTranslator):

    SUITS = {
        "H": "Hearts",
        "D": "Diamonds",
        "C": "Clubs",
        "S": "Spades",
    }

    RANKS = {
        "T": "10",
        "Ace": "A",
        "King": "K",
        "Queen": "Q",
        "Jack": "J",
    }

    ENHANCEMENTS = {
        "BONUS": "Bonus",
        "MULT": "Mult",
        "WILD": "Wild",
        "GLASS": "Glass",
        "STEEL": "Steel",
        "STONE": "Stone",
        "GOLD": "Gold",
        "LUCKY": "Lucky",
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
        "FOIL": "Foil",
        "HOLO": "Holographic",
        "HOLOGRAPHIC": "Holographic",
        "POLYCHROME": "Polychrome",
        "NEGATIVE": "Negative",
        "foil": "Foil",
        "holo": "Holographic",
        "holographic": "Holographic",
        "polychrome": "Polychrome",
        "negative": "Negative",
    }

    SEALS = {
        "RED": "Red",
        "BLUE": "Blue",
        "GOLD": "Gold",
        "PURPLE": "Purple",
    }

    HAND_NAMES = {
        "High Card": "HIGH_CARD",
        "Pair": "PAIR",
        "Two Pair": "TWO_PAIR",
        "Three of a Kind": "THREE_OF_A_KIND",
        "Straight": "STRAIGHT",
        "Flush": "FLUSH",
        "Full House": "FULL_HOUSE",
        "Four of a Kind": "FOUR_OF_A_KIND",
        "Straight Flush": "STRAIGHT_FLUSH",
    }

    def __init__(self):
        self.consumable_factory = LiveConsumableFactory()
        self.joker_factory = LiveJokerFactory()
        self.shop_item_factory = LiveShopItemFactory()

    def translate(
        self,
        snapshot: LiveBalatroSnapshot
    ) -> BalatroState:
        payload = snapshot.payload
        round_info = payload.get("round") or {}
        state = BalatroState()

        state.money = int(payload.get("money", 0))
        state.ante = int(payload.get("ante_num", payload.get("ante", 1)))
        state.round = int(payload.get("round_num", payload.get("round_number", 1)))
        state.score = int(payload.get("score", payload.get("chips", 0)))
        state.blind_score = int(
            round_info.get("chips", payload.get("blind_score", 0))
        )
        state.hands_remaining = int(
            round_info.get("hands_left", payload.get("hands_left", 0))
        )
        state.discards_remaining = int(
            round_info.get("discards_left", payload.get("discards_left", 0))
        )
        state.deck_name = str(
            payload.get("deck", payload.get("deck_name", "RED"))
        ).upper()
        state.stake_name = str(
            payload.get("stake", payload.get("stake_name", "WHITE"))
        ).upper()
        last_tarot_planet = payload.get("last_tarot_planet")
        state.last_tarot_planet = (
            str(last_tarot_planet)
            if isinstance(last_tarot_planet, str) and last_tarot_planet
            else None
        )
        state.phase = snapshot.phase

        hand_area = self._area(payload.get("hand"))
        deck_area = self._area(payload.get("cards", payload.get("deck")))
        owned_deck_present = "owned_cards" in payload or "owned_deck" in payload
        owned_deck_area = self._area(
            payload.get("owned_cards", payload.get("owned_deck"))
        )
        joker_area = self._area(payload.get("jokers"))
        consumable_area = self._area(payload.get("consumables"))
        legacy_shop_area = self._area(payload.get("shop"))
        shop_card_area = self._area(payload.get("shop_jokers"))
        shop_booster_area = self._area(payload.get("shop_boosters"))
        shop_voucher_area = self._area(payload.get("shop_vouchers"))

        state.hand_size = int(
            hand_area.get("limit", len(hand_area.get("cards", [])))
        )
        state.joker_slots = int(joker_area.get("limit", 5))
        state.consumable_slots = int(
            consumable_area.get("limit", 2)
        )
        state.hand = self._cards(hand_area.get("cards", []))
        state.deck = self._cards(deck_area.get("cards", []))
        if owned_deck_present:
            state.owned_deck = self._cards(owned_deck_area.get("cards", []))
        state.jokers = self._jokers(joker_area.get("cards", []))
        state.consumables = self._consumables(
            consumable_area.get("cards", [])
        )

        shop_jokers, shop_consumables = self._shop_cards(
            shop_card_area.get("cards", [])
        )
        state.shop_jokers = shop_jokers
        state.shop_consumables = shop_consumables
        state.shop_consumables.extend(
            self._consumables(legacy_shop_area.get("cards", []))
        )
        state.shop_boosters = self._shop_items(
            shop_booster_area.get("cards", []),
            kind="BOOSTER",
        )
        state.shop_vouchers = self._shop_items(
            shop_voucher_area.get("cards", []),
            kind="VOUCHER",
        )
        state.shop_active = snapshot.phase == "SHOP"

        self._translate_hand_levels(
            state,
            payload.get("hands") or {}
        )
        self._translate_blind(
            state,
            payload.get("blinds") or payload.get("blind")
        )

        return state

    @staticmethod
    def _area(value) -> dict:
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return {
                "cards": value,
                "count": len(value),
                "limit": len(value),
            }
        return {
            "cards": [],
            "count": 0,
            "limit": 0,
        }

    def _cards(self, cards: list[dict]) -> list[BalatroCard]:
        result = []

        for index, card in enumerate(cards):
            value = card.get("value") or card
            rank = value.get("rank")
            suit = value.get("suit")

            if rank is None or suit is None:
                continue

            live_id = card.get("live_id", card.get("id", index))
            result.append(
                self._card(card, live_id)
            )

        return result

    def _jokers(self, values: list[dict]) -> list:
        result = []

        for value in values:
            joker = self.joker_factory.create(value)
            if joker is not None:
                result.append(joker)

        return result

    def _consumables(self, values: list[dict]) -> list:
        result = []

        for index, value in enumerate(values):
            consumable = self.consumable_factory.create(
                value,
                live_id=value.get("live_id", value.get("id", index)),
            )
            if consumable is not None:
                result.append(consumable)

        return result

    def _shop_cards(self, values: list[dict]) -> tuple[list, list]:
        jokers = []
        consumables = []

        for index, value in enumerate(values):
            item_type = str(
                value.get("ability_set", value.get("set", ""))
            ).upper()

            if item_type == "JOKER":
                joker = self.joker_factory.create(value)
                if joker is None:
                    joker = self.shop_item_factory.create(
                        value,
                        kind="JOKER",
                    )
                if joker is not None:
                    jokers.append(joker)
                continue

            consumable = self.consumable_factory.create(
                value,
                live_id=value.get("live_id", value.get("id", index)),
            )
            if consumable is not None:
                consumables.append(consumable)

        return jokers, consumables

    def _shop_items(self, values: list[dict], *, kind: str) -> list:
        result = []
        for value in values:
            item = self.shop_item_factory.create(value, kind=kind)
            if item is not None:
                result.append(item)
        return result

    def _card(
        self,
        card: dict,
        live_id: int | str | None,
    ) -> BalatroCard:
        value = card.get("value") or card
        modifier = card.get("modifier") or card
        rank = str(value["rank"])
        suit = str(value["suit"])
        enhancement = modifier.get("enhancement")
        edition = modifier.get("edition")
        seal = modifier.get("seal")

        return BalatroCard(
            rank=self.RANKS.get(rank, rank),
            suit=self.SUITS.get(suit, suit),
            enhancement=self.ENHANCEMENTS.get(
                enhancement,
                enhancement,
            ),
            edition=self.EDITIONS.get(
                edition,
                edition,
            ),
            seal=self.SEALS.get(
                seal,
                seal,
            ),
            live_id=live_id,
        )

    def _translate_hand_levels(
        self,
        state: BalatroState,
        hands: dict,
    ) -> None:
        for name, data in hands.items():
            hand_type = self.HAND_NAMES.get(name)
            if hand_type is None:
                continue
            values = data or {}
            state.hand_levels[hand_type] = int(values.get("level", 1))
            state.hand_play_counts[hand_type] = int(values.get("played", 0))

    def _translate_blind(
        self,
        state: BalatroState,
        blinds,
    ) -> None:
        blind = self._active_blind(blinds)
        if blind is None:
            return

        blind_type_name = str(
            blind.get("type", "SMALL")
        ).upper()
        blind_type = BlindType.__members__.get(
            blind_type_name,
            BlindType.SMALL,
        )

        state.blind = Blind(
            blind_type,
            int(blind.get("score", blind.get("chips", 0))),
        )

        if blind_type == BlindType.BOSS:
            state.boss_name = blind.get("name")

    @staticmethod
    def _active_blind(blinds) -> dict | None:
        if not isinstance(blinds, dict):
            return None

        if "type" in blinds:
            return blinds

        values = [
            value
            for value in blinds.values()
            if isinstance(value, dict)
        ]

        for status in ("CURRENT", "SELECT"):
            for value in values:
                if str(value.get("status", "")).upper() == status:
                    return value

        return None
