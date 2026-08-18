import random

import pytest

from games.balatro.card import BalatroCard
from games.balatro.consumable import ConsumableContext
from games.balatro.state import BalatroState
from games.balatro.tarots import (
    TAROT_CARDS,
    create_tarot,
    random_tarot,
)


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

    targets = tarot.get_target_cards(state)

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

    tarot = create_tarot("Strength")

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

    tarot = create_tarot("Strength")

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

    tarot = create_tarot("Strength")

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

    tarot = create_tarot("Strength")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[card]
    )

    tarot.use(context)

    assert card.rank == "A"


def test_create_tarot_returns_strength():

    tarot = create_tarot("Strength")

    assert tarot.name == "Strength"
    assert tarot.category == "TAROT"


def test_create_tarot_rejects_unknown_tarot():

    with pytest.raises(KeyError):
        create_tarot("Unknown")


def test_magician_applies_lucky_enhancement():

    first = BalatroCard(
        "2",
        "Hearts"
    )

    second = BalatroCard(
        "K",
        "Spades"
    )

    tarot = create_tarot("The Magician")

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

    tarot = create_tarot("The Magician")

    targets = tarot.get_target_cards(state)

    assert targets == [
        [first],
        [second],
        [third],
        [first, second],
        [first, third],
        [second, third]
    ]


def test_random_tarot_returns_registered_tarot():

    tarot = random_tarot(random.Random())

    assert tarot.name in TAROT_CARDS
    assert tarot.category == "TAROT"


def test_strength_cannot_use_card_not_in_hand():

    state = BalatroState()

    card = BalatroCard(
        "2",
        "Hearts"
    )

    tarot = create_tarot("Strength")

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

    tarot = create_tarot("The Magician")

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

    tarot = create_tarot("Strength")

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

    tarot = create_tarot("The Magician")

    context = ConsumableContext(
        state=state,
        cards=cards
    )

    assert not tarot.can_use(context)


def test_create_tarot_returns_magician():

    tarot = create_tarot("The Magician")

    assert tarot.name == "The Magician"
    assert tarot.category == "TAROT"


def test_random_tarot_uses_rng():

    class TestRng:

        def choice(self, values):
            return "The Magician"

    tarot = random_tarot(TestRng())

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

    tarot = create_tarot("The Empress")

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

    tarot = create_tarot("The Empress")

    targets = tarot.get_target_cards(state)

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

    tarot = create_tarot("The Empress")

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

    tarot = create_tarot("The Empress")

    context = ConsumableContext(
        state=state,
        cards=cards
    )

    assert not tarot.can_use(context)


def test_create_tarot_returns_empress():

    tarot = create_tarot("The Empress")

    assert tarot.name == "The Empress"
    assert tarot.category == "TAROT"


def test_random_tarot_uses_rng_for_empress():

    class TestRng:

        def choice(self, values):
            return "The Empress"

    tarot = random_tarot(TestRng())

    assert tarot.name == "The Empress"


def test_all_tarots_are_registered():

    assert list(TAROT_CARDS) == [
        "The Fool",
        "The Magician",
        "The High Priestess",
        "The Empress",
        "The Emperor",
        "The Hierophant",
        "The Lovers",
        "The Chariot",
        "Justice",
        "The Hermit",
        "The Wheel of Fortune",
        "Strength",
        "The Hanged Man",
        "Death",
        "Temperance",
        "The Devil",
        "The Tower",
        "The Star",
        "The Moon",
        "The Sun",
        "Judgement",
        "The World",
    ]


def test_fool_copies_target():

    target = object()

    tarot = create_tarot("The Fool")

    context = ConsumableContext(
        state=BalatroState(),
        target=target
    )

    tarot.use(context)

    assert context.data["copy"] is target


def test_high_priestess_creates_two_planets():

    class TestRng:

        def choice(self, values):
            return values[0]

    tarot = create_tarot("The High Priestess")

    context = ConsumableContext(
        state=BalatroState(),
        data={"rng": TestRng()}
    )

    tarot.use(context)

    assert len(context.data["created"]) == 2
    assert all(
        planet.category == "PLANET"
        for planet in context.data["created"]
    )


def test_emperor_creates_two_tarots():

    first = create_tarot("The Magician")
    second = create_tarot("The Empress")

    values = iter([first, second])

    tarot = create_tarot("The Emperor")

    context = ConsumableContext(
        state=BalatroState(),
        data={
            "random_tarot": lambda: next(values)
        }
    )

    tarot.use(context)

    assert context.data["created"] == [
        first,
        second
    ]


def test_hierophant_applies_bonus_enhancement():

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("K", "Spades")
    ]

    tarot = create_tarot("The Hierophant")

    context = ConsumableContext(
        state=BalatroState(),
        cards=cards
    )

    tarot.use(context)

    assert all(
        card.enhancement == "Bonus"
        for card in cards
    )


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


def test_justice_rejects_an_already_glass_noop_target():
    card = BalatroCard("2", "Hearts", enhancement="Glass")
    tarot = create_tarot("Justice")
    context = ConsumableContext(state=BalatroState(), cards=[card])

    assert tarot.can_use(context) is False


def test_hermit_doubles_money_with_gain_capped_at_twenty():

    state = BalatroState()
    state.money = 15

    tarot = create_tarot("The Hermit")

    context = ConsumableContext(
        state=state
    )

    tarot.use(context)

    assert state.money == 30
    assert context.data["money"] == 15


def test_hermit_doubles_money_when_below_twenty():

    state = BalatroState()
    state.money = 7

    tarot = create_tarot("The Hermit")

    context = ConsumableContext(
        state=state
    )

    tarot.use(context)

    assert state.money == 14


def test_wheel_of_fortune_applies_edition_on_success():

    class TestRng:

        def random(self):
            return 0.1

        def choice(self, values):
            return "Foil"

    class TestJoker:

        def __init__(self):
            self.edition = None

    joker = TestJoker()

    state = BalatroState()
    state.jokers = [joker]

    tarot = create_tarot("The Wheel of Fortune")

    context = ConsumableContext(
        state=state,
        target=joker,
        data={"rng": TestRng()}
    )

    tarot.use(context)

    assert joker.edition == "Foil"
    assert context.data["edition"] == "Foil"


def test_hanged_man_destroys_selected_cards():

    first = BalatroCard("2", "Hearts")
    second = BalatroCard("3", "Spades")

    state = BalatroState()
    state.hand = [
        first,
        second
    ]

    tarot = create_tarot("The Hanged Man")

    context = ConsumableContext(
        state=state,
        cards=[first, second]
    )

    tarot.use(context)

    assert state.hand == []
    assert state.discard_pile == [
        first,
        second
    ]
    assert context.data["destroyed"] == [
        first,
        second
    ]


def test_death_converts_first_card_to_second():

    source = BalatroCard("2", "Hearts")
    target = BalatroCard("K", "Spades")

    target.enhancement = "Gold"
    target.edition = "Foil"
    target.seal = "Red"

    tarot = create_tarot("Death")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[source, target]
    )

    tarot.use(context)

    assert source.rank == "K"
    assert source.suit == "Spades"
    assert source.enhancement == "Gold"
    assert source.edition == "Foil"
    assert source.seal == "Red"


def test_temperance_uses_joker_sell_values_up_to_fifty():

    class TestJoker:

        def __init__(self, sell_value):
            self.sell_value = sell_value

    state = BalatroState()
    state.jokers = [
        TestJoker(15),
        TestJoker(20),
        TestJoker(30)
    ]

    tarot = create_tarot("Temperance")

    context = ConsumableContext(
        state=state
    )

    tarot.use(context)

    assert context.data["money"] == 50


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


def test_star_changes_selected_cards_to_diamonds():

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Clubs"),
        BalatroCard("4", "Spades")
    ]

    tarot = create_tarot("The Star")

    context = ConsumableContext(
        state=BalatroState(),
        cards=cards
    )

    tarot.use(context)

    assert all(
        card.suit == "Diamonds"
        for card in cards
    )


def test_moon_changes_selected_cards_to_clubs():

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Diamonds"),
        BalatroCard("4", "Spades")
    ]

    tarot = create_tarot("The Moon")

    context = ConsumableContext(
        state=BalatroState(),
        cards=cards
    )

    tarot.use(context)

    assert all(
        card.suit == "Clubs"
        for card in cards
    )


def test_sun_changes_selected_cards_to_hearts():

    cards = [
        BalatroCard("2", "Clubs"),
        BalatroCard("3", "Diamonds"),
        BalatroCard("4", "Spades")
    ]

    tarot = create_tarot("The Sun")

    context = ConsumableContext(
        state=BalatroState(),
        cards=cards
    )

    tarot.use(context)

    assert all(
        card.suit == "Hearts"
        for card in cards
    )


def test_judgement_creates_joker():

    joker = object()

    tarot = create_tarot("Judgement")

    context = ConsumableContext(
        state=BalatroState(),
        data={
            "random_joker": lambda: joker
        }
    )

    tarot.use(context)

    assert context.data["create_joker"]
    assert context.data["joker"] is joker


def test_world_changes_selected_cards_to_spades():

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Diamonds"),
        BalatroCard("4", "Clubs")
    ]

    tarot = create_tarot("The World")

    context = ConsumableContext(
        state=BalatroState(),
        cards=cards
    )

    tarot.use(context)

    assert all(
        card.suit == "Spades"
        for card in cards
    )
