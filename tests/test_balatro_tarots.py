import pytest
import random

from games.balatro.card import BalatroCard
from games.balatro.consumable import ConsumableContext
from games.balatro.state import BalatroState
from games.balatro.tarots import TAROT_CARDS, create_tarot, random_tarot


def test_strength_can_use_with_cards():

    tarot = create_tarot("Strength")

    state = BalatroState()

    card = BalatroCard(
        "2",
        "Hearts"
    )

    state.hand = [
        card
    ]

    context = ConsumableContext(
        state=state,
        cards=[card]
    )

    assert tarot.can_use(context)


def test_strength_cannot_use_without_cards():

    tarot = create_tarot("Strength")

    context = ConsumableContext(
        state=BalatroState()
    )

    assert not tarot.can_use(context)


def test_strength_increases_rank():

    card = BalatroCard(
        "2",
        "Hearts"
    )

    tarot = create_tarot("Strength")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.rank == "3"


def test_strength_does_not_change_ace():

    card = BalatroCard(
        "A",
        "Hearts"
    )

    tarot = create_tarot("Strength")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.rank == "A"


def test_create_tarot_returns_independent_instance():

    first = create_tarot("Strength")
    second = create_tarot("Strength")

    assert first is not second


def test_strength_generates_one_or_two_card_targets():

    state = BalatroState()

    first = BalatroCard("2", "Hearts")
    second = BalatroCard("3", "Spades")
    third = BalatroCard("4", "Clubs")

    state.hand = [
        first,
        second,
        third
    ]

    tarot = create_tarot("Strength")

    targets = tarot.get_target_cards(
        state
    )

    assert targets == [
        [first],
        [second],
        [third],
        [first, second],
        [first, third],
        [second, third]
    ]


def test_strength_increases_jack_to_queen():

    card = BalatroCard(
        "J",
        "Hearts"
    )

    tarot = create_tarot(
        "Strength"
    )

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.rank == "Q"


def test_strength_increases_queen_to_king():

    card = BalatroCard(
        "Q",
        "Hearts"
    )

    tarot = create_tarot(
        "Strength"
    )

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.rank == "K"


def test_strength_increases_king_to_ace():

    card = BalatroCard(
        "K",
        "Hearts"
    )

    tarot = create_tarot(
        "Strength"
    )

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.rank == "A"


def test_strength_does_not_increase_ace():

    card = BalatroCard(
        "A",
        "Hearts"
    )

    tarot = create_tarot(
        "Strength"
    )

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.rank == "A"


def test_create_tarot_returns_strength():

    tarot = create_tarot(
        "Strength"
    )

    assert tarot.name == "Strength"
    assert tarot.category == "TAROT"


def test_create_tarot_rejects_unknown_tarot():

    with pytest.raises(
        KeyError
    ):
        create_tarot(
            "Unknown"
        )


def test_magician_applies_lucky_enhancement():

    first = BalatroCard(
        "2",
        "Hearts"
    )

    second = BalatroCard(
        "K",
        "Spades"
    )

    tarot = create_tarot(
        "The Magician"
    )

    context = ConsumableContext(
        state=BalatroState(),
        cards=[first, second]
    )

    tarot.use(context)

    assert first.enhancement == "Lucky"
    assert second.enhancement == "Lucky"


def test_magician_generates_one_or_two_card_targets():

    state = BalatroState()

    first = BalatroCard("2", "Hearts")
    second = BalatroCard("3", "Spades")
    third = BalatroCard("4", "Clubs")

    state.hand = [
        first,
        second,
        third
    ]

    tarot = create_tarot(
        "The Magician"
    )

    targets = tarot.get_target_cards(
        state
    )

    assert targets == [
        [first],
        [second],
        [third],
        [first, second],
        [first, third],
        [second, third]
    ]


def test_random_tarot_returns_registered_tarot():

    tarot = random_tarot(
        random.Random()
    )

    assert tarot.name in TAROT_CARDS
    assert tarot.category == "TAROT"


def test_strength_cannot_use_card_not_in_hand():

    state = BalatroState()

    card = BalatroCard(
        "2",
        "Hearts"
    )

    tarot = create_tarot(
        "Strength"
    )

    context = ConsumableContext(
        state=state,
        cards=[card]
    )

    assert not tarot.can_use(context)


def test_magician_cannot_use_card_not_in_hand():

    state = BalatroState()

    card = BalatroCard(
        "2",
        "Hearts"
    )

    tarot = create_tarot(
        "The Magician"
    )

    context = ConsumableContext(
        state=state,
        cards=[card]
    )

    assert not tarot.can_use(context)


def test_strength_cannot_use_more_than_two_cards():

    state = BalatroState()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Clubs")
    ]

    state.hand = cards

    tarot = create_tarot(
        "Strength"
    )

    context = ConsumableContext(
        state=state,
        cards=cards
    )

    assert not tarot.can_use(context)


def test_magician_cannot_use_more_than_two_cards():

    state = BalatroState()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Clubs")
    ]

    state.hand = cards

    tarot = create_tarot(
        "The Magician"
    )

    context = ConsumableContext(
        state=state,
        cards=cards
    )

    assert not tarot.can_use(context)


def test_create_tarot_returns_magician():

    tarot = create_tarot(
        "The Magician"
    )

    assert tarot.name == "The Magician"
    assert tarot.category == "TAROT"


def test_random_tarot_uses_rng():

    class TestRng:

        def choice(self, values):
            return "The Magician"

    tarot = random_tarot(
        TestRng()
    )

    assert tarot.name == "The Magician"


def test_empress_applies_mult_enhancement():

    first = BalatroCard(
        "2",
        "Hearts"
    )

    second = BalatroCard(
        "K",
        "Spades"
    )

    tarot = create_tarot(
        "The Empress"
    )

    context = ConsumableContext(
        state=BalatroState(),
        cards=[first, second]
    )

    tarot.use(context)

    assert first.enhancement == "Mult"
    assert second.enhancement == "Mult"


def test_empress_generates_one_or_two_card_targets():

    state = BalatroState()

    first = BalatroCard("2", "Hearts")
    second = BalatroCard("3", "Spades")
    third = BalatroCard("4", "Clubs")

    state.hand = [
        first,
        second,
        third
    ]

    tarot = create_tarot(
        "The Empress"
    )

    targets = tarot.get_target_cards(
        state
    )

    assert targets == [
        [first],
        [second],
        [third],
        [first, second],
        [first, third],
        [second, third]
    ]


def test_empress_cannot_use_card_not_in_hand():

    state = BalatroState()

    card = BalatroCard(
        "2",
        "Hearts"
    )

    tarot = create_tarot(
        "The Empress"
    )

    context = ConsumableContext(
        state=state,
        cards=[card]
    )

    assert not tarot.can_use(context)


def test_empress_cannot_use_more_than_two_cards():

    state = BalatroState()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Clubs")
    ]

    state.hand = cards

    tarot = create_tarot(
        "The Empress"
    )

    context = ConsumableContext(
        state=state,
        cards=cards
    )

    assert not tarot.can_use(context)


def test_create_tarot_returns_empress():

    tarot = create_tarot(
        "The Empress"
    )

    assert tarot.name == "The Empress"
    assert tarot.category == "TAROT"


def test_random_tarot_uses_rng_for_empress():

    class TestRng:

        def choice(self, values):
            return "The Empress"

    tarot = random_tarot(
        TestRng()
    )

    assert tarot.name == "The Empress"


def test_hierophant_applies_bonus_enhancement():

    first = BalatroCard("2", "Hearts")
    second = BalatroCard("K", "Spades")

    tarot = create_tarot("The Hierophant")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[first, second]
    )

    tarot.use(context)

    assert first.enhancement == "Bonus"
    assert second.enhancement == "Bonus"


def test_lovers_applies_wild_enhancement():

    card = BalatroCard("2", "Hearts")

    tarot = create_tarot("The Lovers")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.enhancement == "Wild"


def test_chariot_applies_steel_enhancement():

    card = BalatroCard("2", "Hearts")

    tarot = create_tarot("The Chariot")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.enhancement == "Steel"


def test_justice_applies_glass_enhancement():

    card = BalatroCard("2", "Hearts")

    tarot = create_tarot("Justice")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.enhancement == "Glass"


def test_devil_applies_gold_enhancement():

    card = BalatroCard("2", "Hearts")

    tarot = create_tarot("The Devil")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.enhancement == "Gold"


def test_tower_applies_stone_enhancement():

    card = BalatroCard("2", "Hearts")

    tarot = create_tarot("The Tower")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.enhancement == "Stone"


def test_star_changes_suit_to_diamonds():

    card = BalatroCard("2", "Hearts")

    tarot = create_tarot("The Star")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.suit == "Diamonds"


def test_moon_changes_suit_to_clubs():

    card = BalatroCard("2", "Hearts")

    tarot = create_tarot("The Moon")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.suit == "Clubs"


def test_sun_changes_suit_to_hearts():

    card = BalatroCard("2", "Spades")

    tarot = create_tarot("The Sun")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.suit == "Hearts"


def test_world_changes_suit_to_spades():

    card = BalatroCard("2", "Hearts")

    tarot = create_tarot("The World")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.suit == "Spades"