from games.balatro.card import BalatroCard
from games.balatro.environment import BalatroEnvironment
from games.balatro.actions import DISCARD_CARDS, END_ROUND, PLAY_CARDS, BUY_CONSUMABLE, END_SHOP, USE_CONSUMABLE, BalatroAction
from games.balatro.consumable import Consumable
from games.balatro.planets import create_planet, PLANET_CARDS


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

    environment.execute_action(
        BalatroAction(
            END_SHOP
        )
    )

    assert environment.state.phase == "ROUND_START"
    assert not environment.state.shop_active