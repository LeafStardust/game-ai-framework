from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.the_duo import TheDuoJoker
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.planets import create_planet
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.shop_consumable_policy import (
    HOLD,
    ConsumableAcquisitionPolicy,
    ConsumableAcquisitionThresholds,
)
from games.balatro.state import BalatroState
from games.balatro.strategy import GOLD, BalatroStrategyTracker
from games.balatro.strategy_catalog import UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_value import StrategyAwareConsumableSynergyEvaluator


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def _tracker() -> BalatroStrategyTracker:
    return BalatroStrategyTracker(
        UNIVERSAL_BALATRO_STRATEGIES,
        modifier_provider=lambda state: (
            default_balatro_playbooks().for_state(state).strategy_modifiers()
        ),
    )


def test_strategy_definitions_are_universal_and_red_white_only_modifies_them():
    playbook = default_balatro_playbooks().get("RED", "WHITE")

    assert "straight_flush" in UNIVERSAL_BALATRO_STRATEGIES
    straight_flush = UNIVERSAL_BALATRO_STRATEGIES["straight_flush"]
    assert "neptune" in straight_flush.gold_planets

    modifiers = playbook.strategy_modifiers()
    assert "definitions" not in modifiers
    assert modifiers["strategies"]["straight_flush"]["enabled"] is False
    assert modifiers["strategies"]["straight"]["effectiveness"] == 1.10
    assert modifiers["strategies"]["flush"]["effectiveness"] == 1.10


def test_shared_pair_joker_highlights_pair_not_composite_full_house():
    state = _state()
    state.jokers = [JollyJoker()]
    tracker = _tracker()

    resolution = tracker.observe(state)

    assert resolution.active_strategy_id == "pair"
    assert resolution.assessment("pair").score > resolution.assessment("full_house").score


def test_gold_pair_joker_is_prioritized_inside_highlighted_pair_strategy():
    state = _state()
    state.jokers = [JollyJoker()]
    tracker = _tracker()
    assert tracker.observe(state).active_strategy_id == "pair"

    evaluation = tracker.evaluate_item(
        state,
        TheDuoJoker(),
        kind="JOKER",
    )

    assert evaluation.strategy_id == "pair"
    assert evaluation.tier == GOLD
    assert evaluation.active_alignment
    assert evaluation.value > 8.0


def test_red_white_blocks_neptune_and_other_planets_until_their_strategy_is_active():
    state = _state()
    state.phase = "SHOP"
    state.money = 20
    tracker = _tracker()
    evaluator = StrategyAwareConsumableSynergyEvaluator(
        strategy_tracker=tracker,
    )
    thresholds = ConsumableAcquisitionThresholds.from_mapping(
        default_balatro_playbooks().for_state(state).thresholds_for("D4")
    )
    policy = ConsumableAcquisitionPolicy(
        thresholds,
        evaluator=evaluator,
    )

    neptune = create_planet("NEPTUNE")
    jupiter = create_planet("JUPITER")

    assert tracker.evaluate_item(state, neptune, kind="PLANET").tier is None
    assert evaluator.evaluate(neptune, state).total_gain < 0.0
    assert policy.decide(state, neptune).action == HOLD

    # Flush is enabled in Red/White, but a random Jupiter still cannot choose the
    # build by itself. Planets refine an active strategy instead of starting one.
    assert evaluator.evaluate(jupiter, state).total_gain < 0.0
    assert policy.decide(state, jupiter).action == HOLD


def test_active_pair_strategy_admits_mercury_but_rejects_off_strategy_jupiter():
    state = _state()
    state.phase = "SHOP"
    state.money = 20
    state.jokers = [JollyJoker()]
    tracker = _tracker()
    assert tracker.observe(state).active_strategy_id == "pair"

    evaluator = StrategyAwareConsumableSynergyEvaluator(
        strategy_tracker=tracker,
    )
    mercury = create_planet("MERCURY")
    jupiter = create_planet("JUPITER")

    mercury_value = evaluator.evaluate(mercury, state)
    jupiter_value = evaluator.evaluate(jupiter, state)

    assert mercury_value.total_gain > 0.0
    assert jupiter_value.total_gain < 0.0


def test_d1_prefers_active_strategic_hand_when_survival_layer_considers_lines_equal():
    state = _state()
    state.jokers = [JollyJoker()]
    tracker = _tracker()
    assert tracker.observe(state).active_strategy_id == "pair"
    policy = StrategyAwareLiveHandActionPolicy(
        strategy_tracker=tracker,
    )

    pair = BalatroAction(
        PLAY_CARDS,
        [
            BalatroCard("A", "Spades"),
            BalatroCard("A", "Hearts"),
        ],
    )
    high_card = BalatroAction(
        PLAY_CARDS,
        [
            BalatroCard("A", "Spades"),
            BalatroCard("K", "Hearts"),
        ],
    )

    pair_fit, _ = policy._strategy_fit(state, pair)
    high_card_fit, _ = policy._strategy_fit(state, high_card)

    assert pair_fit > 0.0
    assert pair_fit > high_card_fit
