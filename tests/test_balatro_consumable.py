from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.state import BalatroState


class TestConsumable(Consumable):

    name = "Test Consumable"
    category = "TEST"

    def can_use(self, context):
        return True

    def use(self, context):
        context.state.money += 10
        return context


def test_consumable_context_creation():

    state = BalatroState()
    context = ConsumableContext(state=state)

    assert context.state is state
    assert context.cards == []
    assert context.target is None
    assert context.data == {}


def test_consumable_usage():

    state = BalatroState()
    consumable = TestConsumable()
    context = ConsumableContext(state=state)

    assert consumable.name == "Test Consumable"
    assert consumable.category == "TEST"
    assert consumable.can_use(context)

    consumable.use(context)

    assert state.money == 10
