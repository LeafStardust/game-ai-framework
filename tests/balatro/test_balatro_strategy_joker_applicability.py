import pytest

from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.cloud_9 import Cloud9Joker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.misprint import MisprintJoker
from games.balatro.jokers.the_duo import TheDuoJoker
from games.balatro.joker_policy import (
    REPLACE,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.state import BalatroState
from games.balatro.strategy import GOLD, SILVER, BalatroStrategyTracker, StrategyDefinition
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_joker_applicability import OFF_PATH, UNIVERSAL
from games.balatro.strategy_tree_catalog import TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY
from games.balatro.strategy_tree_tracker import TreeAwareStateAwareBalatroStrategyTracker
from games.balatro.strategy_value import (
    StrategyAwareJokerBuildTransitionPlanner,
    StrategyAwareJokerBuildValueEvaluator,
)


class PairAnchorJoker:
    pass


class FlushAnchorJoker:
    pass


def _runtime_tracker():
    return TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
    )


def _pair_state(*, ante=6):
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = ante
    state.money = 25
    state.jokers = [TheDuoJoker()]
    return state


@pytest.mark.parametrize("joker_type", (MisprintJoker, BullJoker, Cloud9Joker))
def test_portable_joker_keeps_intrinsic_value_under_committed_pair(joker_type):
    state = _pair_state()
    evaluator = StrategyAwareJokerBuildValueEvaluator(
        strategy_tracker=_runtime_tracker(),
    )

    value = evaluator.evaluate(state, joker_type())

    assert value.applicability == UNIVERSAL
    assert value.base_total_gain > 0.0
    assert value.strategic_adjustment == pytest.approx(0.0)
    assert value.total_gain == pytest.approx(value.base_total_gain)
    assert not any("generic probe discount" in note for note in value.rationale)


def test_flush_only_joker_is_off_path_and_loses_flush_probe_value_under_pair():
    state = _pair_state()
    evaluator = StrategyAwareJokerBuildValueEvaluator(
        strategy_tracker=_runtime_tracker(),
    )

    value = evaluator.evaluate(state, CraftyJoker())

    assert value.applicability == OFF_PATH
    assert value.direct_scoring_gain == pytest.approx(0.0)
    assert value.active_alignment is False
    assert value.pivot_candidate is False
    assert value.strategic_adjustment < -value.base_total_gain
    assert value.total_gain < 0.0


def test_committed_pair_replaces_flush_only_joker_with_universal_value():
    state = _pair_state()
    state.joker_slots = 2
    state.jokers.append(CraftyJoker())
    candidate = MisprintJoker()
    candidate.cost = 0
    evaluator = StrategyAwareJokerBuildValueEvaluator(
        strategy_tracker=_runtime_tracker(),
    )
    planner = StrategyAwareJokerBuildTransitionPlanner(evaluator=evaluator)
    thresholds = JokerAcquisitionThresholds(
        minimum_purchase_advantage=0.0,
        minimum_replacement_advantage=0.0,
        aligned_minimum_replacement_advantage=0.0,
        minimum_purchase_build_gain=0.0,
        minimum_replacement_build_delta=0.0,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
    )

    decision = JokerAcquisitionPolicy(
        thresholds,
        transition_planner=planner,
    ).decide(state, candidate)

    assert decision.action == REPLACE
    assert decision.selected is not None
    assert decision.selected.replace_index == 1
    assert decision.selected.replace_joker == "CraftyJoker"


def _two_strategy_tracker():
    return BalatroStrategyTracker(
        {
            "pair": StrategyDefinition(
                strategy_id="pair",
                name="Pair",
                primary_hands=("PAIR",),
                gold_jokers=frozenset({"pairanchorjoker"}),
            ),
            "flush": StrategyDefinition(
                strategy_id="flush",
                name="Flush",
                primary_hands=("FLUSH",),
                silver_jokers=frozenset({"flushanchorjoker", "craftyjoker"}),
            ),
        }
    )


def _two_strategy_state(ante):
    state = BalatroState()
    state.ante = ante
    state.jokers = [PairAnchorJoker(), FlushAnchorJoker()]
    return state


def test_ante_six_makes_dominant_strategy_exclusive_for_items_and_hands():
    ante_five = _two_strategy_state(5)
    ante_six = _two_strategy_state(6)
    tracker = _two_strategy_tracker()

    before_lock = tracker.evaluate_item(ante_five, CraftyJoker(), kind="JOKER")
    after_lock = tracker.evaluate_item(ante_six, CraftyJoker(), kind="JOKER")
    pair_fit, _ = tracker.hand_fit(ante_six, "PAIR")
    flush_fit, _ = tracker.hand_fit(ante_six, "FLUSH")

    resolution = tracker.observe(ante_six)
    assert resolution.dominant_strategy_id == "pair"
    assert resolution.relevant_strategy_ids == ("flush",)
    assert before_lock.active_alignment is True
    assert before_lock.value > 0.0
    assert after_lock.active_alignment is False
    assert after_lock.pivot_candidate is False
    assert after_lock.value < 0.0
    assert pair_fit > 0.0
    assert flush_fit < 0.0
