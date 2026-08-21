from types import SimpleNamespace

from games.balatro.actions import BUY_BOOSTER, BalatroAction
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.shop_booster_policy import BUY, HOLD, BoosterAcquisitionThresholds
from games.balatro.spectrals import create_spectral
from games.balatro.state import BalatroState
from games.balatro.strategy import BalatroStrategyTracker
from games.balatro.strategy_booster_policy import StrategyAwareShopBoosterPolicy
from games.balatro.strategy_catalog import UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_value import StrategyAwareConsumableSynergyEvaluator
from games.balatro.tarots import create_tarot


def _state(*, ante: int = 1) -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.money = 20
    state.ante = ante
    return state


def _tracker() -> BalatroStrategyTracker:
    return BalatroStrategyTracker(
        UNIVERSAL_BALATRO_STRATEGIES,
        modifier_provider=lambda state: (
            default_balatro_playbooks().for_state(state).strategy_modifiers()
        ),
    )


def _booster_thresholds() -> BoosterAcquisitionThresholds:
    # Remove economic admission noise so these tests isolate D8 family/strategy
    # policy. The normal Red/White thresholds remain covered by playbook tests.
    return BoosterAcquisitionThresholds(
        minimum_buy_advantage=0.0,
        minimum_pack_hit_probability=0.0,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_target=0,
        reserve_weight=0.0,
    )


def _booster_action(label: str) -> BalatroAction:
    return BalatroAction(
        BUY_BOOSTER,
        target=SimpleNamespace(label=label, price=0),
    )


def test_weak_scoring_readiness_defers_arcana_but_keeps_spectral_exploration_safe():
    state = _state()
    policy = StrategyAwareShopBoosterPolicy(
        thresholds=_booster_thresholds(),
        strategy_tracker=_tracker(),
    )

    arcana = policy.recommend(state, _booster_action("Arcana Pack"))
    spectral = policy.recommend(state, _booster_action("Spectral Pack"))

    # Five-run calibration: generic Arcana spending is deferred while the board has
    # essentially no real scoring capacity, but Spectral remains exempt so rare
    # high-upside effects (including Soul access) are still available.
    assert arcana.decision == HOLD
    assert spectral.decision == BUY
    assert any("scoring-readiness gate" in note for note in arcana.rationale)
    assert any("autonomous-safe" in note for note in spectral.rationale)


def test_celestial_pack_is_blocked_without_real_poker_hand_strategy_evidence():
    state = _state()
    policy = StrategyAwareShopBoosterPolicy(
        thresholds=_booster_thresholds(),
        strategy_tracker=_tracker(),
    )

    recommendation = policy.recommend(
        state,
        _booster_action("Celestial Pack"),
    )

    assert recommendation.decision == HOLD
    assert any("Celestial blocked" in note for note in recommendation.rationale)
    assert any("refinement spending" in note for note in recommendation.rationale)


def test_celestial_pack_unlocks_after_meaningful_poker_hand_strategy_and_usage_evidence():
    state = _state()
    state.jokers = [JollyJoker()]
    state.hand_levels["PAIR"] = 2
    state.hand_play_counts["PAIR"] = 8
    tracker = _tracker()
    assert tracker.observe(state).assessment("pair").score >= 3.5
    policy = StrategyAwareShopBoosterPolicy(
        thresholds=_booster_thresholds(),
        strategy_tracker=tracker,
    )

    recommendation = policy.recommend(
        state,
        _booster_action("Celestial Pack"),
    )

    assert recommendation.decision == BUY
    assert any("Celestial admitted" in note for note in recommendation.rationale)
    assert any("most-played hand=PAIR plays=8/8" in note for note in recommendation.rationale)


def test_early_tarot_and_spectral_seeders_are_not_penalized_without_strategy():
    state = _state(ante=1)
    evaluator = StrategyAwareConsumableSynergyEvaluator(
        strategy_tracker=_tracker(),
    )

    tarot = evaluator.evaluate(create_tarot("The Sun"), state)
    spectral = evaluator.evaluate(create_spectral("Sigil"), state)

    assert tarot.strategic_adjustment >= 0.0
    assert spectral.strategic_adjustment >= 0.0
    assert any("early TAROT remains exploration-eligible" in note for note in tarot.rationale)
    assert any("early SPECTRAL remains exploration-eligible" in note for note in spectral.rationale)


def test_late_off_shortlist_structural_tarot_is_suppressed_not_hard_banned():
    state = _state(ante=6)
    state.jokers = [JollyJoker()]
    tracker = _tracker()
    assert tracker.observe(state).dominant_strategy_id == "pair"
    evaluator = StrategyAwareConsumableSynergyEvaluator(
        strategy_tracker=tracker,
    )

    result = evaluator.evaluate(create_tarot("The Sun"), state)

    assert result.strategic_adjustment < 0.0
    assert any("late off-shortlist TAROT penalty" in note for note in result.rationale)
    assert result.total_gain == result.base_evaluation.total_gain + result.strategic_adjustment
