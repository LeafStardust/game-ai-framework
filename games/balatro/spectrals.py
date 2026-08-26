import copy

from games.balatro.card import BalatroCard, ENHANCEMENTS
from games.balatro.consumable import ConsumableContext, SpectralCard


RANKS = [
    "2", "3", "4", "5", "6",
    "7", "8", "9", "10",
    "J", "Q", "K", "A"
]

NUMBERED_RANKS = tuple(RANKS[:9])
FACE_RANKS = ("J", "Q", "K")

SUITS = [
    "Hearts",
    "Diamonds",
    "Clubs",
    "Spades"
]

# Familiar/Grim/Incantation create Enhanced cards that retain a real rank. Stone
# removes rank identity and is excluded by Balatro's generated Enhanced-card pool.
# Keep this pool ordered so seeded/offline callers do not depend on Python set order.
GENERATED_ENHANCEMENTS = tuple(sorted(ENHANCEMENTS - {"Stone"}))


def _random_enhanced_card(rng, *, ranks) -> BalatroCard:
    return BalatroCard(
        rng.choice(ranks),
        rng.choice(SUITS),
        enhancement=rng.choice(GENERATED_ENHANCEMENTS),
    )


def _editionless_jokers(state) -> list:
    return [
        joker
        for joker in getattr(state, "jokers", ())
        if getattr(joker, "edition", None) in (None, "")
    ]


def _roll_vanilla_edition(rng) -> str:
    roll = rng.random()
    if roll < 0.50:
        return "Foil"
    if roll < 0.85:
        return "Holographic"
    return "Polychrome"


class Familiar(SpectralCard):

    def __init__(self):
        super().__init__("Familiar")

    def can_use(self, context: ConsumableContext) -> bool:
        return len(context.state.hand) > 1

    def use(
        self,
        context: ConsumableContext
    ) -> ConsumableContext:
        rng = context.data["rng"]
        destroyed = rng.choice(context.state.hand)

        context.state.hand.remove(destroyed)
        context.state.discard_pile.append(destroyed)

        created = [
            _random_enhanced_card(rng, ranks=FACE_RANKS)
            for _ in range(3)
        ]
        context.state.deck.extend(created)
        context.data["destroyed"] = destroyed
        context.data["created"] = created

        return context


class Grim(SpectralCard):

    def __init__(self):
        super().__init__("Grim")

    def can_use(self, context: ConsumableContext) -> bool:
        return len(context.state.hand) > 1

    def use(self, context: ConsumableContext) -> ConsumableContext:
        rng = context.data["rng"]
        destroyed = rng.choice(context.state.hand)

        context.state.hand.remove(destroyed)
        context.state.discard_pile.append(destroyed)

        created = [
            _random_enhanced_card(rng, ranks=("A",))
            for _ in range(2)
        ]

        context.state.deck.extend(created)
        context.data["destroyed"] = destroyed
        context.data["created"] = created

        return context


class Incantation(SpectralCard):

    def __init__(self):
        super().__init__("Incantation")

    def can_use(self, context: ConsumableContext) -> bool:
        return len(context.state.hand) > 1

    def use(self, context: ConsumableContext) -> ConsumableContext:
        rng = context.data["rng"]
        destroyed = rng.choice(context.state.hand)

        context.state.hand.remove(destroyed)
        context.state.discard_pile.append(destroyed)

        created = [
            _random_enhanced_card(rng, ranks=NUMBERED_RANKS)
            for _ in range(4)
        ]

        context.state.deck.extend(created)
        context.data["destroyed"] = destroyed
        context.data["created"] = created

        return context


class Talisman(SpectralCard):

    def __init__(self):
        super().__init__("Talisman")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.cards[0].seal = "Gold"
        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [[card] for card in state.hand]


class Aura(SpectralCard):

    def __init__(self):
        super().__init__("Aura")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
            and getattr(context.cards[0], "edition", None) in (None, "")
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        edition = _roll_vanilla_edition(context.data["rng"])
        context.cards[0].edition = edition
        context.data["edition"] = edition
        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            [card]
            for card in state.hand
            if getattr(card, "edition", None) in (None, "")
        ]


class Wraith(SpectralCard):

    def __init__(self):
        super().__init__("Wraith")

    def can_use(self, context: ConsumableContext) -> bool:
        joker_slots = max(
            0,
            int(getattr(context.state, "joker_slots", 5) or 5),
        )
        return len(context.state.jokers) < joker_slots

    def use(self, context: ConsumableContext) -> ConsumableContext:
        # Wraith's generated Joker is explicitly Rare. Keep that contract
        # distinct from generic random-Joker generation so callers cannot
        # accidentally sample Common/Uncommon outcomes.
        joker = context.data["random_rare_joker"]()

        context.state.jokers.append(joker)
        context.state.money = 0

        context.data["joker"] = joker

        return context


class Sigil(SpectralCard):

    def __init__(self):
        super().__init__("Sigil")

    def can_use(self, context: ConsumableContext) -> bool:
        return len(context.state.hand) > 1

    def use(self, context: ConsumableContext) -> ConsumableContext:
        suit = context.data["rng"].choice(SUITS)

        for card in context.state.hand:
            card.suit = suit

        context.data["suit"] = suit

        return context


class Ouija(SpectralCard):

    def __init__(self):
        super().__init__("Ouija")

    def can_use(self, context: ConsumableContext) -> bool:
        return len(context.state.hand) > 1

    def use(self, context: ConsumableContext) -> ConsumableContext:
        rank = context.data["rng"].choice(RANKS)

        for card in context.state.hand:
            card.rank = rank

        context.state.hand_size -= 1
        context.data["rank"] = rank

        return context


class Ectoplasm(SpectralCard):

    def __init__(self):
        super().__init__("Ectoplasm")

    def can_use(self, context: ConsumableContext) -> bool:
        return bool(_editionless_jokers(context.state))

    def use(self, context: ConsumableContext) -> ConsumableContext:
        joker = context.data["rng"].choice(
            _editionless_jokers(context.state)
        )

        joker.edition = "Negative"
        # The live game increases this penalty for repeated Ectoplasm uses. The
        # framework currently lacks authoritative run-level Ectoplasm-use history,
        # so the first-use mechanical transition remains modeled while policy stays
        # deferred until that public history is observed.
        context.state.hand_size -= 1

        context.data["joker"] = joker

        return context


class Immolate(SpectralCard):

    def __init__(self):
        super().__init__("Immolate")

    def can_use(self, context: ConsumableContext) -> bool:
        return len(context.state.hand) >= 5

    def use(
        self,
        context: ConsumableContext
    ) -> ConsumableContext:

        destroyed = context.data["rng"].sample(
            context.state.hand,
            5
        )

        for card in destroyed:
            context.state.hand.remove(card)
            context.state.discard_pile.append(card)

        context.state.money += 20
        context.data["destroyed"] = destroyed
        context.data["money"] = 20

        return context


class Ankh(SpectralCard):

    def __init__(self):
        super().__init__("Ankh")

    def can_use(self, context: ConsumableContext) -> bool:
        return bool(context.state.jokers)

    def use(self, context: ConsumableContext) -> ConsumableContext:
        jokers = list(context.state.jokers)
        joker = context.data["rng"].choice(jokers)

        copied = copy.deepcopy(joker)
        if str(getattr(copied, "edition", "") or "").upper() == "NEGATIVE":
            copied.edition = None

        survivors = [
            owned
            for owned in jokers
            if owned is joker or bool(getattr(owned, "eternal", False))
        ]
        context.state.jokers = [*survivors, copied]

        context.data["joker"] = joker
        context.data["created"] = copied

        return context


class DejaVu(SpectralCard):

    def __init__(self):
        super().__init__("Deja Vu")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.cards[0].seal = "Red"
        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [[card] for card in state.hand]


class Hex(SpectralCard):

    def __init__(self):
        super().__init__("Hex")

    def can_use(self, context: ConsumableContext) -> bool:
        return bool(_editionless_jokers(context.state))

    def use(self, context: ConsumableContext) -> ConsumableContext:
        jokers = list(context.state.jokers)
        joker = context.data["rng"].choice(
            _editionless_jokers(context.state)
        )

        joker.edition = "Polychrome"
        context.state.jokers = [
            owned
            for owned in jokers
            if owned is joker or bool(getattr(owned, "eternal", False))
        ]

        context.data["joker"] = joker

        return context


class Trance(SpectralCard):

    def __init__(self):
        super().__init__("Trance")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.cards[0].seal = "Blue"
        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [[card] for card in state.hand]


class Medium(SpectralCard):

    def __init__(self):
        super().__init__("Medium")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.cards[0].seal = "Purple"
        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [[card] for card in state.hand]


class Cryptid(SpectralCard):

    def __init__(self):
        super().__init__("Cryptid")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        source = context.cards[0]
        created = [
            copy.deepcopy(source)
            for _ in range(2)
        ]

        context.state.deck.extend(created)
        context.data["created"] = created

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [[card] for card in state.hand]


class Soul(SpectralCard):

    def __init__(self):
        super().__init__("The Soul")

    def can_use(self, context: ConsumableContext) -> bool:
        joker_slots = max(
            0,
            int(getattr(context.state, "joker_slots", 5) or 5),
        )
        return len(context.state.jokers) < joker_slots

    def use(self, context: ConsumableContext) -> ConsumableContext:
        joker = context.data["random_legendary_joker"]()

        context.state.jokers.append(joker)
        context.data["joker"] = joker

        return context


class BlackHole(SpectralCard):

    def __init__(self):
        super().__init__("Black Hole")

    def can_use(self, context: ConsumableContext) -> bool:
        return True

    def use(self, context: ConsumableContext) -> ConsumableContext:
        for hand_type in context.state.hand_levels:
            context.state.hand_levels[hand_type] += 1

        return context


SPECTRAL_CARDS = {
    "Familiar": Familiar,
    "Grim": Grim,
    "Incantation": Incantation,
    "Talisman": Talisman,
    "Aura": Aura,
    "Wraith": Wraith,
    "Sigil": Sigil,
    "Ouija": Ouija,
    "Ectoplasm": Ectoplasm,
    "Immolate": Immolate,
    "Ankh": Ankh,
    "Deja Vu": DejaVu,
    "Hex": Hex,
    "Trance": Trance,
    "Medium": Medium,
    "Cryptid": Cryptid,
    "The Soul": Soul,
    "Black Hole": BlackHole,
}


def create_spectral(name: str) -> SpectralCard:
    return SPECTRAL_CARDS[name]()


def random_spectral(rng) -> SpectralCard:
    return create_spectral(
        rng.choice(list(SPECTRAL_CARDS))
    )
