from types import SimpleNamespace

import pytest

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.state import BalatroState
from games.balatro.unlock_campaign import (
    AUTO,
    HIT_THE_ROAD,
    STUNTMAN,
    UnlockCampaignConfig,
    UnlockCampaignPolicy,
)


def _plan(clear_probability: float):
    return SimpleNamespace(
        value=SimpleNamespace(clear_probability=clear_probability),
    )


def _state(target: str) -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.discards_remaining = 3
    state.joker_unlocks = {
        f"j_{target}": {"unlocked": False},
    }
    return state


def test_unlock_campaign_is_default_off_and_auto_expands_supported_targets():
    assert UnlockCampaignConfig().enabled is False
    assert UnlockCampaignConfig.from_targets([AUTO]).targets == (
        HIT_THE_ROAD,
        STUNTMAN,
    )


def test_unlock_campaign_rejects_unknown_targets():
    with pytest.raises(ValueError, match="unsupported Joker unlock"):
        UnlockCampaignConfig.from_targets(["unknown"])


def test_hit_the_road_discards_five_jacks_only_when_clear_probability_is_preserved():
    state = _state(HIT_THE_ROAD)
    state.hand = [
        BalatroCard("J", suit)
        for suit in ("Spades", "Hearts", "Clubs", "Diamonds", "Spades")
    ]
    policy = UnlockCampaignPolicy(UnlockCampaignConfig((HIT_THE_ROAD,)))

    recommendation = policy.recommend_hand(
        state,
        baseline_plan=_plan(0.75),
        evaluate_forced_action=lambda _action: _plan(0.75),
        play_actions=(),
        project_play=lambda _action: None,
    )

    assert recommendation is not None
    assert recommendation.target_id == HIT_THE_ROAD
    assert recommendation.action.name == DISCARD_CARDS
    assert len(recommendation.action.cards) == 5

    rejected = policy.recommend_hand(
        state,
        baseline_plan=_plan(0.75),
        evaluate_forced_action=lambda _action: _plan(0.74),
        play_actions=(),
        project_play=lambda _action: None,
    )
    assert rejected is None


def test_stuntman_uses_a_guaranteed_hundred_million_play_without_reducing_safety():
    state = _state(STUNTMAN)
    ace = BalatroCard("A", "Spades")
    action = BalatroAction(PLAY_CARDS, cards=[ace])
    policy = UnlockCampaignPolicy(UnlockCampaignConfig((STUNTMAN,)))

    recommendation = policy.recommend_hand(
        state,
        baseline_plan=_plan(1.0),
        evaluate_forced_action=lambda _action: _plan(1.0),
        play_actions=(action,),
        project_play=lambda _action: SimpleNamespace(hand_score=100_000_000),
    )

    assert recommendation is not None
    assert recommendation.target_id == STUNTMAN
    assert recommendation.action is action


def test_unlock_campaign_fails_closed_on_unknown_or_already_unlocked_status():
    policy = UnlockCampaignPolicy(UnlockCampaignConfig((HIT_THE_ROAD,)))
    state = BalatroState()
    assert policy.active_targets(state) == ()

    state.joker_unlocks = {"j_hit_the_road": {"unlocked": True}}
    assert policy.active_targets(state) == ()
