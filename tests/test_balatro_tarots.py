from games.balatro.card import BalatroCard
from games.balatro.consumable import ConsumableContext
from games.balatro.state import BalatroState
from games.balatro.tarots import create_tarot


def test_strength_can_use_with_cards():

    tarot = create_tarot("Strength")

    context = ConsumableContext(
        state=BalatroState(),
        cards=[
            BalatroCard(
                "2",
                "Hearts"
            )
        ]
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