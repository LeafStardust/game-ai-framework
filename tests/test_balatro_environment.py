from games.balatro.card import BalatroCard
from games.balatro.environment import BalatroEnvironment
from games.balatro.actions import DISCARD_CARDS, END_ROUND, PLAY_CARDS, BUY_CONSUMABLE, END_SHOP, REFRESH_SHOP, USE_CONSUMABLE, BalatroAction
from games.balatro.consumable import Consumable
from games.balatro.planets import create_planet, PLANET_CARDS
from games.balatro.tarots import create_tarot


class TestConsumable(Consumable):

    name = "Test Consumable"
    category = "TEST"

    def can_use(self, context):
        return True

    def use(self, context):
        context.state.money += 10
        return context


def test_balatro_environment_has_initial_actions():

    environment = BalatroEnvironment()

    environment.state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Hearts"),
        BalatroCard("10", "Hearts")
    ]

    actions = environment.get_actions()

    action_names = [
        action.name
        for action in actions
    ]

    assert "PLAY_CARDS" in action_names
    assert "DISCARD_CARDS" in action_names
    assert "END_ROUND" in action_names


def test_PLAY_CARDS_changes_phase():

    environment = BalatroEnvironment()

    action = BalatroAction(
        PLAY_CARDS,
        cards=[
            BalatroCard("A", "Hearts"),
            BalatroCard("K", "Hearts"),
            BalatroCard("Q", "Hearts"),
            BalatroCard("J", "Hearts"),
            BalatroCard("10", "Hearts")
        ]
    )

    environment.execute_action(
        action
    )

    assert environment.state.phase == "SHOP"
    assert environment.state.shop_active
    assert len(
        environment.state.shop_consumables
    ) == 2


def test_end_round_increases_round():

    environment = BalatroEnvironment()

    action = BalatroAction(
        END_ROUND
    )

    environment.execute_action(
        action
    )

    assert environment.state.round == 2


def test_balatro_environment_generates_play_actions():

    environment = BalatroEnvironment()

    environment.state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Hearts"),
        BalatroCard("10", "Hearts")
    ]

    actions = environment.get_actions()

    play_actions = [
        action
        for action in actions
        if action.name == PLAY_CARDS
    ]

    assert len(play_actions) == 1


def test_simulate_action_does_not_modify_original_state():

    environment = BalatroEnvironment()

    original_state = environment.get_state()
    original_round = original_state.round

    simulated_state = environment.simulate_action(
        BalatroAction(PLAY_CARDS)
    )

    assert original_state.round == original_round
    assert simulated_state.round == original_round + 1


def test_simulate_action_returns_independent_state():

    environment = BalatroEnvironment()

    simulated_state = environment.simulate_action(
        BalatroAction(END_ROUND)
    )

    simulated_state.round = 99

    assert environment.state.round != 99


def test_simulate_discard_changes_hand():

    environment = BalatroEnvironment()

    environment.state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts")
    ]

    simulated = environment.simulate_action(
        BalatroAction(
            DISCARD_CARDS,
            cards=environment.state.hand.copy()
        )
    )

    assert len(simulated.hand) == 2
    assert simulated.discards_remaining == 2
    assert len(environment.state.hand) == 2


def test_balatro_environment_generates_consumable_actions():

    environment = BalatroEnvironment()
    consumable = TestConsumable()
    environment.state.consumables.append(consumable)

    actions = environment.get_actions()

    consumable_actions = [
        action
        for action in actions
        if action.name == USE_CONSUMABLE
    ]

    assert len(consumable_actions) == 1
    assert consumable_actions[0].target is consumable


def test_use_consumable_changes_state_and_removes_consumable():

    environment = BalatroEnvironment()
    consumable = TestConsumable()
    environment.state.consumables.append(consumable)

    environment.execute_action(
        BalatroAction(
            USE_CONSUMABLE,
            target=consumable
        )
    )

    assert environment.state.money == 10
    assert consumable not in environment.state.consumables


def test_simulate_consumable_does_not_modify_original_state():

    environment = BalatroEnvironment()
    consumable = TestConsumable()
    environment.state.consumables.append(consumable)

    simulated = environment.simulate_action(
        BalatroAction(
            USE_CONSUMABLE,
            target=consumable
        )
    )

    assert environment.state.money == 0
    assert len(environment.state.consumables) == 1
    assert simulated.money == 10
    assert len(simulated.consumables) == 0


def test_planet_can_be_used_through_environment():

    environment = BalatroEnvironment()
    planet = create_planet("MERCURY")

    environment.state.consumables.append(
        planet
    )

    actions = environment.get_actions()

    action = next(
        action
        for action in actions
        if action.name == USE_CONSUMABLE
    )

    environment.execute_action(action)

    assert environment.state.hand_levels["PAIR"] == 2
    assert planet not in environment.state.consumables


def test_environment_generates_planet():

    environment = BalatroEnvironment()

    planet = environment._generate_planet()

    assert planet.category == "PLANET"
    assert planet.name in [
        planet.name
        for planet in PLANET_CARDS.values()
    ]


def test_environment_uses_state_consumable_inventory():

    environment = BalatroEnvironment()
    consumable = create_planet("MERCURY")

    assert environment.state.add_consumable(
        consumable
    )

    assert consumable in environment.state.consumables


def test_buy_consumable_moves_consumable_to_inventory():

    environment = BalatroEnvironment()

    consumable = create_planet("MERCURY")

    environment.state.phase = "SHOP"
    environment.state.shop_active = True
    environment.state.shop_consumables.append(
        consumable
    )
    environment.state.money = consumable.price

    actions = environment.get_actions()

    buy_actions = [
        action
        for action in actions
        if action.name == BUY_CONSUMABLE
    ]

    assert len(buy_actions) == 1
    assert buy_actions[0].target is consumable

    environment.execute_action(
        buy_actions[0]
    )

    assert consumable in environment.state.consumables
    assert consumable not in environment.state.shop_consumables


def test_buy_consumable_fails_when_inventory_is_full():

    environment = BalatroEnvironment()

    first = create_planet("MERCURY")
    second = create_planet("VENUS")
    third = create_planet("EARTH")

    environment.state.add_consumable(first)
    environment.state.add_consumable(second)

    environment.state.shop_consumables.append(
        third
    )

    actions = environment.get_actions()

    buy_actions = [
        action
        for action in actions
        if action.name == BUY_CONSUMABLE
    ]

    assert len(buy_actions) == 0

    environment.execute_action(
        BalatroAction(
            BUY_CONSUMABLE,
            target=third
        )
    )

    assert third not in environment.state.consumables
    assert third in environment.state.shop_consumables


def test_complete_blind_generates_shop_consumables():

    environment = BalatroEnvironment()

    environment._complete_blind(
        environment.state
    )

    assert len(
        environment.state.shop_consumables
    ) == 2

    assert environment.state.shop_active


def test_completed_blind_enters_shop():

    environment = BalatroEnvironment()

    environment._complete_blind(
        environment.state
    )

    assert environment.state.phase == "SHOP"
    assert environment.state.shop_active
    assert len(
        environment.state.shop_consumables
    ) == 2


def test_shop_generates_buy_and_end_actions():

    environment = BalatroEnvironment()

    environment._complete_blind(
        environment.state
    )

    environment.state.money = max(
        consumable.price
        for consumable in environment.state.shop_consumables
    )

    actions = environment.get_actions()

    buy_actions = [
        action
        for action in actions
        if action.name == BUY_CONSUMABLE
    ]

    end_actions = [
        action
        for action in actions
        if action.name == END_SHOP
    ]

    assert len(buy_actions) == 2
    assert len(end_actions) == 1


def test_end_shop_returns_to_round_start():

    environment = BalatroEnvironment()

    environment._complete_blind(
        environment.state
    )

    blind = environment.state.blind

    environment.execute_action(
        BalatroAction(
            END_SHOP
        )
    )

    assert environment.state.phase == "ROUND_START"
    assert not environment.state.shop_active
    assert environment.state.blind is blind


def test_buy_consumable_spends_money():

    environment = BalatroEnvironment()

    consumable = create_planet("MERCURY")

    environment.state.phase = "SHOP"
    environment.state.shop_active = True
    environment.state.shop_consumables.append(
        consumable
    )
    environment.state.money = consumable.price

    environment.execute_action(
        BalatroAction(
            BUY_CONSUMABLE,
            target=consumable
        )
    )

    assert environment.state.money == 0
    assert consumable in environment.state.consumables
    assert consumable not in environment.state.shop_consumables


def test_buy_consumable_requires_enough_money():

    environment = BalatroEnvironment()

    consumable = create_planet("MERCURY")

    environment.state.phase = "SHOP"
    environment.state.shop_active = True
    environment.state.shop_consumables.append(
        consumable
    )
    environment.state.money = consumable.price - 1

    actions = environment.get_actions()

    buy_actions = [
        action
        for action in actions
        if action.name == BUY_CONSUMABLE
    ]

    assert len(buy_actions) == 0


def test_simulate_buy_consumable_does_not_modify_original_state():

    environment = BalatroEnvironment()

    consumable = create_planet("MERCURY")

    environment.state.phase = "SHOP"
    environment.state.shop_active = True
    environment.state.shop_consumables.append(
        consumable
    )
    environment.state.money = consumable.price

    simulated_state = environment.simulate_action(
        BalatroAction(
            BUY_CONSUMABLE,
            target=consumable
        )
    )

    assert consumable in environment.state.shop_consumables
    assert consumable not in environment.state.consumables
    assert environment.state.money == consumable.price

    assert consumable in simulated_state.consumables
    assert consumable not in simulated_state.shop_consumables
    assert simulated_state.money == 0


def test_simulate_end_shop_does_not_modify_original_state():

    environment = BalatroEnvironment()

    environment._complete_blind(
        environment.state
    )

    simulated_state = environment.simulate_action(
        BalatroAction(
            END_SHOP
        )
    )

    assert environment.state.phase == "SHOP"
    assert environment.state.shop_active

    assert simulated_state.phase == "ROUND_START"
    assert not simulated_state.shop_active


def test_shop_generates_refresh_action():

    environment = BalatroEnvironment()

    environment._complete_blind(
        environment.state
    )

    environment.state.money = environment.SHOP_REFRESH_COST

    actions = environment.get_actions()

    refresh_actions = [
        action
        for action in actions
        if action.name == REFRESH_SHOP
    ]

    assert len(refresh_actions) == 1


def test_refresh_shop_costs_money():

    environment = BalatroEnvironment()

    environment._complete_blind(
        environment.state
    )

    environment.state.money = environment.SHOP_REFRESH_COST

    environment.execute_action(
        BalatroAction(
            REFRESH_SHOP
        )
    )

    assert environment.state.money == 0
    assert len(
        environment.state.shop_consumables
    ) == 2


def test_refresh_shop_requires_money():

    environment = BalatroEnvironment()

    environment._complete_blind(
        environment.state
    )

    environment.state.money = (
        environment.SHOP_REFRESH_COST - 1
    )

    actions = environment.get_actions()

    refresh_actions = [
        action
        for action in actions
        if action.name == REFRESH_SHOP
    ]

    assert len(refresh_actions) == 0


def test_refresh_shop_does_not_spend_money_when_unaffordable():

    environment = BalatroEnvironment()

    environment._complete_blind(
        environment.state
    )

    environment.state.money = (
        environment.SHOP_REFRESH_COST - 1
    )

    original = environment.state.shop_consumables.copy()

    environment.execute_action(
        BalatroAction(
            REFRESH_SHOP
        )
    )

    assert environment.state.money == (
        environment.SHOP_REFRESH_COST - 1
    )

    assert environment.state.shop_consumables == original


def test_use_consumable_action_contains_target_cards():

    environment = BalatroEnvironment()

    consumable = create_planet("MERCURY")

    environment.state.consumables.append(
        consumable
    )

    actions = environment.get_actions()

    use_actions = [
        action
        for action in actions
        if action.name == USE_CONSUMABLE
    ]

    assert len(use_actions) == 1
    assert use_actions[0].target is consumable
    assert use_actions[0].cards == []


def test_strength_can_be_used_through_environment():

    environment = BalatroEnvironment()

    first = BalatroCard(
        "2",
        "Hearts"
    )

    second = BalatroCard(
        "3",
        "Spades"
    )

    environment.state.hand = [
        first,
        second
    ]

    consumable = create_tarot(
        "Strength"
    )

    environment.state.consumables.append(
        consumable
    )

    actions = environment.get_actions()

    use_actions = [
        action
        for action in actions
        if action.name == USE_CONSUMABLE
        and action.target is consumable
    ]

    assert len(use_actions) == 3

    two_card_action = next(
        action
        for action in use_actions
        if action.cards == [first, second]
    )

    environment.execute_action(
        two_card_action
    )

    assert first.rank == "3"
    assert second.rank == "4"


def test_shop_can_generate_tarot():

    environment = BalatroEnvironment()

    environment.rng.random = lambda: 1.0

    environment._generate_shop_consumables(
        environment.state
    )

    assert len(
        environment.state.shop_consumables
    ) == 2

    assert all(
        consumable.category == "TAROT"
        for consumable in environment.state.shop_consumables
    )


def test_environment_generates_consumable():

    environment = BalatroEnvironment()

    consumable = environment._generate_consumable()

    assert consumable.category in {
        "PLANET",
        "TAROT"
    }


def test_shop_can_generate_registered_tarot():

    environment = BalatroEnvironment()

    environment.rng.random = lambda: 1.0

    tarot_names = set()

    for _ in range(20):

        environment._generate_shop_consumables(
            environment.state
        )

        tarot_names.update(
            consumable.name
            for consumable in environment.state.shop_consumables
        )

    assert tarot_names == {
        "Strength",
        "The Magician"
    }


def test_magician_can_be_used_through_environment():

    environment = BalatroEnvironment()

    first = BalatroCard(
        "2",
        "Hearts"
    )

    second = BalatroCard(
        "K",
        "Spades"
    )

    environment.state.hand = [
        first,
        second
    ]

    consumable = create_tarot(
        "The Magician"
    )

    environment.state.consumables.append(
        consumable
    )

    actions = environment.get_actions()

    use_actions = [
        action
        for action in actions
        if action.name == USE_CONSUMABLE
        and action.target is consumable
    ]

    assert len(use_actions) == 3

    two_card_action = next(
        action
        for action in use_actions
        if action.cards == [first, second]
    )

    environment.execute_action(
        two_card_action
    )

    assert first.enhancement == "Lucky"
    assert second.enhancement == "Lucky"
    assert consumable not in environment.state.consumables


def test_invalid_consumable_target_does_not_change_state():

    environment = BalatroEnvironment()

    card = BalatroCard(
        "2",
        "Hearts"
    )

    target = BalatroCard(
        "3",
        "Spades"
    )

    environment.state.hand = [
        card
    ]

    consumable = create_tarot(
        "Strength"
    )

    environment.state.consumables.append(
        consumable
    )

    action = BalatroAction(
        USE_CONSUMABLE,
        cards=[target],
        target=consumable
    )

    environment.execute_action(
        action
    )

    assert target.rank == "3"
    assert consumable in environment.state.consumables