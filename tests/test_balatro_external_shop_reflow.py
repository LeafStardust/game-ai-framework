from types import SimpleNamespace

from games.balatro.actions import BUY_CONSUMABLE, BalatroAction
from games.balatro.live.external.shop_mouse import (
    ShopClickSequence,
    ShopMouseLayout,
    ShopPointerStep,
)
from games.balatro.live.external.shop_reflow import ShopMainReflowLocator
from games.balatro.live.external.viewport import NormalizedPoint
from games.balatro.state import BalatroState


class Executor:
    def __init__(self, layout):
        self.layout = layout


def _action(target):
    return BalatroAction(BUY_CONSUMABLE, target=target)


def test_reflow_sequence_moves_card_anchor_and_preserves_buy_offset():
    target = SimpleNamespace(area_index=1, label="The Sun", cost=3)
    layout = ShopMouseLayout(
        main={
            1: ShopClickSequence(
                (
                    ShopPointerStep("click", NormalizedPoint(0.6567, 0.4936)),
                    ShopPointerStep("click", NormalizedPoint(0.6567, 0.5736)),
                )
            )
        }
    )
    locator = ShopMainReflowLocator(Executor(layout))

    sequence = locator._retarget_sequence(
        _action(target),
        NormalizedPoint(0.6100, 0.4900),
    )

    assert sequence.steps[0].point.x == 0.6100
    assert sequence.steps[0].point.y == 0.4900
    assert sequence.steps[1].point.x == 0.6100
    assert abs(sequence.steps[1].point.y - 0.5700) < 1e-9


def test_remaining_main_offers_preserve_original_area_order_after_split_translation():
    state = BalatroState()
    joker = SimpleNamespace(area_index=2, label="Joker")
    consumable_a = SimpleNamespace(area_index=0, label="Tarot A")
    consumable_b = SimpleNamespace(area_index=1, label="Tarot B")
    state.shop_jokers = [joker]
    state.shop_consumables = [consumable_b, consumable_a]

    offers = ShopMainReflowLocator._remaining_main_offers(state)

    assert offers == [consumable_a, consumable_b, joker]
