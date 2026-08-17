from games.balatro.actions import SELECT_BLIND
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.state import BalatroState
from games.balatro.strategy import BalatroStrategyTracker
from games.balatro.strategy_blind_skip_policy import StrategyAwareBlindSkipPolicy
from games.balatro.strategy_catalog import UNIVERSAL_BALATRO_STRATEGIES


def _state(*, ante=6, pair_evidence=True) -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = ante
    state.money = 0
    if pair_evidence:
        state.jokers = [JollyJoker()]
    return state


def _tracker() -> BalatroStrategyTracker:
    return BalatroStrategyTracker(
        UNIVERSAL_BALATRO_STRATEGIES,
        modifier_provider=lambda state: (
            default_balatro_playbooks().for_state(state).strategy_modifiers()
        ),
    )


def _policy() -> StrategyAwareBlindSkipPolicy:
    return StrategyAwareBlindSkipPolicy(strategy_tracker=_tracker())


def _snapshot(*, blind_type="SMALL", tag="tag_meteor", reward=3):
    return LiveBalatroSnapshot(
        sequence=1,
        phase="BLIND_SELECT",
        state_complete=True,
        payload={
            "money": 0,
            "blind": {
                "type": blind_type,
                "tag": tag,
                "reward": reward,
            },
        },
    )


def _thresholds(state):
    from games.balatro.blind_skip_policy import BlindSkipThresholds

    return BlindSkipThresholds.from_mapping(
        default_balatro_playbooks().for_state(state).thresholds_for("D13")
    )


def test_d13_zero_strategy_evidence_keeps_tag_adjustment_neutral():
    state = _state(pair_evidence=False)
    decision = _policy().decide(
        _snapshot(tag="tag_meteor"),
        state,
        thresholds=_thresholds(state),
    )

    assert decision.dominant_strategy_id is None
    assert decision.strategy_tag_adjustment == 0.0
    assert decision.strategy_tag_support == "no-positive-strategy-evidence"


def test_d13_meteor_tag_reinforces_evidenced_pair_strategy():
    state = _state()
    decision = _policy().decide(
        _snapshot(tag="tag_meteor"),
        state,
        thresholds=_thresholds(state),
    )

    assert decision.dominant_strategy_id == "pair"
    assert decision.strategy_tag_adjustment > 0.0
    assert "pair" in decision.strategy_tag_support


def test_d13_orbital_tag_rewards_most_played_hand_matching_pair_strategy():
    state = _state()
    state.hand_play_counts["PAIR"] = 5
    state.hand_play_counts["HIGH_CARD"] = 2

    decision = _policy().decide(
        _snapshot(tag="tag_orbital"),
        state,
        thresholds=_thresholds(state),
    )

    assert decision.dominant_strategy_id == "pair"
    assert decision.strategy_tag_adjustment > 0.0
    assert decision.strategy_tag_support == "supports:pair"


def test_d13_orbital_tag_is_bounded_penalty_when_it_upgrades_off_strategy_hand_late():
    state = _state()
    state.hand_play_counts["HIGH_CARD"] = 5
    state.hand_play_counts["PAIR"] = 2

    decision = _policy().decide(
        _snapshot(tag="tag_orbital"),
        state,
        thresholds=_thresholds(state),
    )

    assert decision.dominant_strategy_id == "pair"
    assert decision.strategy_tag_adjustment < 0.0
    assert decision.strategy_tag_adjustment >= -2.5
    assert decision.strategy_tag_support == "off-shortlist-development-tag"


def test_d13_choice_preserving_pack_tag_is_not_penalized_when_unmatched():
    state = _state()
    decision = _policy().decide(
        _snapshot(tag="tag_voucher"),
        state,
        thresholds=_thresholds(state),
    )

    assert decision.strategy_tag_adjustment == 0.0
    assert decision.strategy_tag_support == "choice-preserving-tag-neutral"


def test_d13_strategy_tag_value_does_not_override_big_blind_boss_preparation_cost():
    state = _state()
    state.hand_play_counts["PAIR"] = 4

    decision = _policy().decide(
        _snapshot(blind_type="BIG", tag="tag_meteor", reward=4),
        state,
        thresholds=_thresholds(state),
    )

    assert decision.strategy_tag_adjustment > 0.0
    assert decision.boss_preparation_cost > 0.0
    assert decision.action_name == SELECT_BLIND
