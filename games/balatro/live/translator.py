from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.consumable_factory import LiveConsumableFactory
from games.balatro.live.interfaces import BalatroStateTranslator
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.shop import LiveShopItemFactory
from games.balatro.state import BalatroState


class DefaultBalatroStateTranslator(BalatroStateTranslator):

    SUITS = {"H": "Hearts", "D": "Diamonds", "C": "Clubs", "S": "Spades"}
    RANKS = {"T": "10", "Ace": "A", "King": "K", "Queen": "Q", "Jack": "J"}
    ENHANCEMENTS = {
        "BONUS": "Bonus", "MULT": "Mult", "WILD": "Wild", "GLASS": "Glass",
        "STEEL": "Steel", "STONE": "Stone", "GOLD": "Gold", "LUCKY": "Lucky",
        "m_bonus": "Bonus", "m_mult": "Mult", "m_wild": "Wild", "m_glass": "Glass",
        "m_steel": "Steel", "m_stone": "Stone", "m_gold": "Gold", "m_lucky": "Lucky",
    }
    EDITIONS = {
        "FOIL": "Foil", "HOLO": "Holographic", "HOLOGRAPHIC": "Holographic",
        "POLYCHROME": "Polychrome", "NEGATIVE": "Negative", "foil": "Foil",
        "holo": "Holographic", "holographic": "Holographic",
        "polychrome": "Polychrome", "negative": "Negative",
    }
    SEALS = {"RED": "Red", "BLUE": "Blue", "GOLD": "Gold", "PURPLE": "Purple"}
    HAND_NAMES = {
        "High Card": "HIGH_CARD", "Pair": "PAIR", "Two Pair": "TWO_PAIR",
        "Three of a Kind": "THREE_OF_A_KIND", "Straight": "STRAIGHT", "Flush": "FLUSH",
        "Full House": "FULL_HOUSE", "Four of a Kind": "FOUR_OF_A_KIND",
        "Straight Flush": "STRAIGHT_FLUSH", "Five of a Kind": "FIVE_OF_A_KIND",
        "Flush House": "FLUSH_HOUSE", "Flush Five": "FLUSH_FIVE",
    }

    def __init__(self):
        self.consumable_factory = LiveConsumableFactory()
        self.joker_factory = LiveJokerFactory()
        self.shop_item_factory = LiveShopItemFactory()

    def translate(self, snapshot: LiveBalatroSnapshot) -> BalatroState:
        payload = snapshot.payload
        round_info = payload.get("round") or {}
        state = BalatroState()
        state.money = int(payload.get("money", 0))
        state.ante = int(payload.get("ante_num", payload.get("ante", 1)))
        state.round = int(payload.get("round_num", payload.get("round_number", 1)))
        state.score = int(payload.get("score", payload.get("chips", 0)))
        state.blind_score = int(round_info.get("chips", payload.get("blind_score", 0)))
        state.hands_remaining = int(round_info.get("hands_left", payload.get("hands_left", 0)))
        state.discards_remaining = int(round_info.get("discards_left", payload.get("discards_left", 0)))
        discards_used = round_info.get("discards_used", payload.get("discards_used"))
        state.discards_used = max(0, int(discards_used)) if discards_used is not None else None
        most_played = round_info.get(
            "most_played_poker_hand",
            round_info.get(
                "most_played_hand",
                payload.get("most_played_poker_hand", payload.get("most_played_hand")),
            ),
        )
        if isinstance(most_played, str) and most_played:
            state.round_most_played_hand = self.HAND_NAMES.get(most_played, most_played)
        state.deck_name = str(payload.get("deck", payload.get("deck_name", "RED"))).upper()
        state.stake_name = str(payload.get("stake", payload.get("stake_name", "WHITE"))).upper()
        last_tarot_planet = payload.get("last_tarot_planet")
        state.last_tarot_planet = str(last_tarot_planet) if isinstance(last_tarot_planet, str) and last_tarot_planet else None
        joker_unlocks = payload.get("joker_unlocks")
        state.joker_unlocks = (
            {str(key): {str(field): bool(field_value) for field, field_value in value.items() if isinstance(field_value, bool)}
             for key, value in joker_unlocks.items() if isinstance(value, dict)}
            if isinstance(joker_unlocks, dict) else {}
        )
        state.phase = snapshot.phase

        hand_area = self._area(payload.get("hand"))
        deck_area = self._area(payload.get("cards", payload.get("deck")))
        owned_deck_present = "owned_cards" in payload or "owned_deck" in payload
        owned_deck_area = self._area(payload.get("owned_cards", payload.get("owned_deck")))
        joker_area = self._area(payload.get("jokers"))
        consumable_area = self._area(payload.get("consumables"))
        legacy_shop_area = self._area(payload.get("shop"))
        shop_card_area = self._area(payload.get("shop_jokers"))
        shop_booster_area = self._area(payload.get("shop_boosters"))
        shop_voucher_area = self._area(payload.get("shop_vouchers"))

        state.hand_size = int(hand_area.get("limit", len(hand_area.get("cards", []))))
        state.consumable_slots = int(consumable_area.get("limit", 2))
        state.hand = self._cards(hand_area.get("cards", []))
        state.deck = self._cards(deck_area.get("cards", []))
        if owned_deck_present:
            state.owned_deck = self._cards(owned_deck_area.get("cards", []))

        raw_jokers = list(joker_area.get("cards", []))
        state.jokers = self._jokers(raw_jokers)
        authoritative_limit = max(0, int(joker_area.get("limit", 5) or 0))
        authoritative_count = max(
            0,
            int(joker_area.get("count", len(raw_jokers)) or 0),
            len(raw_jokers),
        )
        unmodeled_occupancy = max(0, authoritative_count - len(state.jokers))
        state.joker_slots = max(0, authoritative_limit - unmodeled_occupancy)

        state.consumables = self._consumables(consumable_area.get("cards", []))
        shop_jokers, shop_consumables = self._shop_cards(shop_card_area.get("cards", []))
        state.shop_jokers = shop_jokers
        state.shop_consumables = shop_consumables
        state.shop_consumables.extend(self._consumables(legacy_shop_area.get("cards", [])))
        state.shop_boosters = self._shop_items(shop_booster_area.get("cards", []), kind="BOOSTER")
        state.shop_vouchers = self._shop_items(shop_voucher_area.get("cards", []), kind="VOUCHER")
        state.shop_active = snapshot.phase == "SHOP"
        self._translate_hand_levels(state, payload.get("hands") or {})
        self._translate_blind(state, payload.get("blinds") or payload.get("blind"))
        return state

    @staticmethod
    def _area(value) -> dict:
        if isinstance(value, dict): return value
        if isinstance(value, list): return {"cards": value, "count": len(value), "limit": len(value)}
        return {"cards": [], "count": 0, "limit": 0}

    def _cards(self, cards: list[dict]) -> list[BalatroCard]:
        result = []
        for index, card in enumerate(cards):
            value = card.get("value") or card
            rank, suit = value.get("rank"), value.get("suit")
            if rank is None or suit is None: continue
            live_id = card.get("live_id", card.get("id", index))
            result.append(self._card(card, live_id))
        return result

    def _jokers(self, values: list[dict]) -> list:
        result = []
        for value in values:
            joker = self.joker_factory.create(value)
            if joker is not None: result.append(joker)
        return result

    def _consumables(self, values: list[dict]) -> list:
        result = []
        for index, value in enumerate(values):
            consumable = self.consumable_factory.create(value, live_id=value.get("live_id", value.get("id", index)))
            if consumable is not None: result.append(consumable)
        return result

    def _shop_cards(self, values: list[dict]) -> tuple[list, list]:
        jokers, consumables = [], []
        for index, value in enumerate(values):
            item_type = str(value.get("ability_set", value.get("set", ""))).upper()
            if item_type == "JOKER":
                joker = self.joker_factory.create(value)
                if joker is None: joker = self.shop_item_factory.create(value, kind="JOKER")
                if joker is not None: jokers.append(joker)
                continue
            consumable = self.consumable_factory.create(value, live_id=value.get("live_id", value.get("id", index)))
            if consumable is not None: consumables.append(consumable)
        return jokers, consumables

    def _shop_items(self, values: list[dict], *, kind: str) -> list:
        result = []
        for value in values:
            item = self.shop_item_factory.create(value, kind=kind)
            if item is not None: result.append(item)
        return result

    def _card(self, card: dict, live_id: int | str | None) -> BalatroCard:
        value = card.get("value") or card
        modifier = card.get("modifier") or card
        rank, suit = str(value["rank"]), str(value["suit"])
        enhancement, edition, seal = modifier.get("enhancement"), modifier.get("edition"), modifier.get("seal")
        return BalatroCard(
            rank=self.RANKS.get(rank, rank), suit=self.SUITS.get(suit, suit),
            enhancement=self.ENHANCEMENTS.get(enhancement, enhancement),
            edition=self.EDITIONS.get(edition, edition), seal=self.SEALS.get(seal, seal),
            live_id=live_id, debuffed=bool(card.get("debuff", False)),
            permanent_bonus=int(card.get("permanent_bonus", 0) or 0),
            forced_selection=bool(card.get("forced_selection", False)),
        )

    def _translate_hand_levels(self, state: BalatroState, hands: dict) -> None:
        for name, data in hands.items():
            hand_type = self.HAND_NAMES.get(name)
            if hand_type is None: continue
            values = data or {}
            state.hand_levels[hand_type] = int(values.get("level", 1))
            state.hand_play_counts[hand_type] = int(values.get("played", 0))
            state.round_hand_play_counts[hand_type] = int(values.get("played_this_round", 0))

    def _translate_blind(self, state: BalatroState, blinds) -> None:
        blind = self._active_blind(blinds)
        if blind is None: return
        blind_type_name = str(blind.get("type", "SMALL")).upper()
        blind_type = BlindType.__members__.get(blind_type_name, BlindType.SMALL)
        state.blind = Blind(blind_type, int(blind.get("score", blind.get("chips", 0))), int(blind.get("reward", 0)))
        if blind_type == BlindType.BOSS:
            state.boss_name = blind.get("name")
            boss_name = str(state.boss_name or "")
            if boss_name == "The Eye" and "hands" in blind:
                values = blind.get("hands") or []
                if isinstance(values, (list, tuple, set)):
                    state.boss_blind_hands = {self.HAND_NAMES.get(str(name), str(name)) for name in values}
                state.boss_blind_state_observed = True
            if boss_name == "The Mouth" and "only_hand" in blind:
                only_hand = blind.get("only_hand")
                state.boss_blind_only_hand = self.HAND_NAMES.get(str(only_hand), str(only_hand)) if only_hand else None
                state.boss_blind_state_observed = True

    @staticmethod
    def _active_blind(blinds) -> dict | None:
        if not isinstance(blinds, dict): return None
        if "type" in blinds: return blinds
        values = [value for value in blinds.values() if isinstance(value, dict)]
        for status in ("CURRENT", "SELECT"):
            for value in values:
                if str(value.get("status", "")).upper() == status: return value
        return None