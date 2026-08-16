from games.balatro.card import BalatroCard
from games.balatro.consumable import ConsumableContext
from games.balatro.state import BalatroState
from games.balatro.spectrals import (
    SPECTRAL_CARDS,
    create_spectral,
)


def test_all_spectrals_are_registered():

    assert list(SPECTRAL_CARDS) == [
        "Familiar",
        "Grim",
        "Incantation",
        "Talisman",
        "Aura",
        "Wraith",
        "Sigil",
        "Ouija",
        "Ectoplasm",
        "Immolate",
        "Ankh",
        "Deja Vu",
        "Hex",
        "Trance",
        "Medium",
        "Cryptid",
        "The Soul",
        "Black Hole",
    ]


def test_familiar_destroys_one_card_and_creates_three_faces():

    class Rng:

        def choice(self, values):
            return values[0]

    state = BalatroState()
    card = BalatroCard("2", "Hearts")
    state.hand = [card]

    spectral = create_spectral("Familiar")

    context = ConsumableContext(
        state=state,
        data={"rng": Rng()}
    )

    spectral.use(context)

    assert card not in state.hand
    assert card in state.discard_pile
    assert len(context.data["created"]) == 3
    assert all(
        card.rank in {"J", "Q", "K"}
        for card in context.data["created"]
    )


def test_grim_creates_two_aces():

    class Rng:

        def choice(self, values):
            return values[0]

    state = BalatroState()
    state.hand = [
        BalatroCard("2", "Hearts")
    ]

    spectral = create_spectral("Grim")

    context = ConsumableContext(
        state=state,
        data={"rng": Rng()}
    )

    spectral.use(context)

    assert len(context.data["created"]) == 2
    assert all(
        card.rank == "A"
        for card in context.data["created"]
    )


def test_incantation_creates_four_numbered_cards():

    class Rng:

        def choice(self, values):
            return values[0]

    state = BalatroState()
    state.hand = [
        BalatroCard("2", "Hearts")
    ]

    spectral = create_spectral("Incantation")

    context = ConsumableContext(
        state=state,
        data={"rng": Rng()}
    )

    spectral.use(context)

    assert len(context.data["created"]) == 4
    assert all(
        card.rank in {
            "2", "3", "4", "5", "6",
            "7", "8", "9", "10"
        }
        for card in context.data["created"]
    )


def test_talisman_applies_gold_seal():

    card = BalatroCard("2", "Hearts")
    state = BalatroState()
    state.hand = [card]

    spectral = create_spectral("Talisman")

    context = ConsumableContext(
        state=state,
        cards=[card]
    )

    spectral.use(context)

    assert card.seal == "Gold"


def test_aura_applies_edition():

    class Rng:

        def choice(self, values):
            return "Foil"

    card = BalatroCard("2", "Hearts")
    state = BalatroState()
    state.hand = [card]

    spectral = create_spectral("Aura")

    context = ConsumableContext(
        state=state,
        cards=[card],
        data={"rng": Rng()}
    )

    spectral.use(context)

    assert card.edition == "Foil"
    assert context.data["edition"] == "Foil"


def test_wraith_creates_rare_joker_and_sets_money_to_zero():

    joker = object()

    state = BalatroState()
    state.money = 25

    spectral = create_spectral("Wraith")

    context = ConsumableContext(
        state=state,
        data={
            "random_joker": lambda: joker
        }
    )

    spectral.use(context)

    assert state.money == 0
    assert state.jokers == [joker]


def test_sigil_changes_hand_to_one_suit():

    class Rng:

        def choice(self, values):
            return "Diamonds"

    state = BalatroState()
    state.hand = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Clubs"),
        BalatroCard("4", "Spades"),
    ]

    spectral = create_spectral("Sigil")

    context = ConsumableContext(
        state=state,
        data={"rng": Rng()}
    )

    spectral.use(context)

    assert all(
        card.suit == "Diamonds"
        for card in state.hand
    )


def test_ouija_changes_hand_to_one_rank_and_reduces_hand_size():

    class Rng:

        def choice(self, values):
            return "A"

    state = BalatroState()
    state.hand = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Clubs"),
    ]

    spectral = create_spectral("Ouija")

    context = ConsumableContext(
        state=state,
        data={"rng": Rng()}
    )

    spectral.use(context)

    assert all(
        card.rank == "A"
        for card in state.hand
    )
    assert state.hand_size == 7


def test_ectoplasm_adds_negative_and_reduces_hand_size():

    class Rng:

        def choice(self, values):
            return values[0]

    class Joker:

        edition = None

    joker = Joker()

    state = BalatroState()
    state.jokers = [joker]

    spectral = create_spectral("Ectoplasm")

    context = ConsumableContext(
        state=state,
        data={"rng": Rng()}
    )

    spectral.use(context)

    assert joker.edition == "Negative"
    assert state.hand_size == 7


def test_immolate_destroys_five_cards_and_gives_money():

    class Rng:

        def sample(self, values, amount):
            return values[:amount]

    state = BalatroState()
    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
    ]
    state.hand = cards.copy()
    state.money = 5

    spectral = create_spectral("Immolate")

    context = ConsumableContext(
        state=state,
        data={"rng": Rng()}
    )

    spectral.use(context)

    assert state.hand == []
    assert state.discard_pile == cards
    assert state.money == 25


def test_ankh_copies_one_joker_and_destroys_the_rest():

    class Joker:

        def __init__(self, name):
            self.name = name

    first = Joker("First")
    second = Joker("Second")

    state = BalatroState()
    state.jokers = [first, second]

    spectral = create_spectral("Ankh")

    context = ConsumableContext(
        state=state,
        data={
            "rng": type(
                "Rng",
                (),
                {"choice": lambda self, values: values[0]}
            )()
        }
    )

    spectral.use(context)

    assert len(state.jokers) == 2
    assert state.jokers[0] is first
    assert state.jokers[1] is not first
    assert state.jokers[1].name == "First"
    assert second not in state.jokers


def test_deja_vu_applies_red_seal():

    card = BalatroCard("2", "Hearts")
    state = BalatroState()
    state.hand = [card]

    spectral = create_spectral("Deja Vu")

    context = ConsumableContext(
        state=state,
        cards=[card]
    )

    spectral.use(context)

    assert card.seal == "Red"


def test_hex_applies_polychrome_and_destroys_other_jokers():

    class Rng:

        def choice(self, values):
            return values[0]

    class Joker:

        def __init__(self, name):
            self.name = name
            self.edition = None

    first = Joker("First")
    second = Joker("Second")

    state = BalatroState()
    state.jokers = [first, second]

    spectral = create_spectral("Hex")

    context = ConsumableContext(
        state=state,
        data={"rng": Rng()}
    )

    spectral.use(context)

    assert state.jokers == [first]
    assert first.edition == "Polychrome"


def test_trance_applies_blue_seal():

    card = BalatroCard("2", "Hearts")
    state = BalatroState()
    state.hand = [card]

    spectral = create_spectral("Trance")

    context = ConsumableContext(
        state=state,
        cards=[card]
    )

    spectral.use(context)

    assert card.seal == "Blue"


def test_medium_applies_purple_seal():

    card = BalatroCard("2", "Hearts")
    state = BalatroState()
    state.hand = [card]

    spectral = create_spectral("Medium")

    context = ConsumableContext(
        state=state,
        cards=[card]
    )

    spectral.use(context)

    assert card.seal == "Purple"


def test_cryptid_creates_two_exact_copies():

    card = BalatroCard(
        "A",
        "Spades",
        enhancement="Steel",
        edition="Foil",
        seal="Red"
    )

    state = BalatroState()
    state.hand = [card]

    spectral = create_spectral("Cryptid")

    context = ConsumableContext(
        state=state,
        cards=[card]
    )

    spectral.use(context)

    created = context.data["created"]

    assert len(created) == 2
    assert created[0] == card
    assert created[1] == card
    assert created[0] is not card
    assert created[1] is not card


def test_soul_creates_legendary_joker():

    joker = object()

    state = BalatroState()

    spectral = create_spectral("The Soul")

    context = ConsumableContext(
        state=state,
        data={
            "random_legendary_joker": lambda: joker
        }
    )

    spectral.use(context)

    assert state.jokers == [joker]


def test_black_hole_upgrades_every_poker_hand():

    state = BalatroState()
    original = state.hand_levels.copy()

    spectral = create_spectral("Black Hole")

    context = ConsumableContext(
        state=state
    )

    spectral.use(context)

    for hand_type, level in original.items():
        assert state.hand_levels[hand_type] == level + 1