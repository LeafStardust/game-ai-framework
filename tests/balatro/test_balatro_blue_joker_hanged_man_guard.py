from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
from games.balatro.live.strategy_consumable_timing import (
    StrategyAwareConsumableTargetEvaluator,
)


class BlueJoker:
    pass


class _BaseTargetEvaluator:
    def supports(self, consumable):
        return True

    def rank_targets(self, state, consumable):
        return ("base-target",)


class _Tracker:
    def observe(self, state):
        raise AssertionError("Blue Joker Hanged Man guard must fire before strategy lookup")


def test_inventory_hanged_man_has_no_targets_while_blue_joker_is_owned() -> None:
    evaluator = StrategyAwareConsumableTargetEvaluator(
        _BaseTargetEvaluator(),
        strategy_tracker=_Tracker(),
    )
    state = SimpleNamespace(jokers=[BlueJoker()])
    hanged_man = SimpleNamespace(name="The Hanged Man")

    assert evaluator.rank_targets(state, hanged_man) == ()


def test_arcana_pack_does_not_offer_hanged_man_while_blue_joker_is_owned() -> None:
    state = SimpleNamespace(
        phase="TAROT_PACK",
        joker_slots=5,
        jokers=[BlueJoker()],
    )
    choice = LivePackChoice(
        area_index=0,
        address=100,
        data={
            "ability_set": "TAROT",
            "label": "The Hanged Man",
            "live_id": 200,
        },
    )

    actions = LivePackActionGenerator().generate_actions(state, [choice])

    assert [action.name for action in actions] == [SKIP_BOOSTER]
    assert all(action.name != SELECT_PACK_CARD for action in actions)
