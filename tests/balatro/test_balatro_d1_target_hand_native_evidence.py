from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
import games.balatro.live.strategy_hand_policy as strategy_hand_policy
import games.balatro.target_hand_engine_policy as target_hand_engine_policy


class RunnerJoker:
    pass


def _card(rank: str, suit: str):
    return SimpleNamespace(
        rank=rank,
        suit=suit,
        enhancement=None,
        edition=None,
        seal=None,
        debuffed=False,
    )


def _neutralize_other_strategy_evidence(monkeypatch, policy):
    monkeypatch.setattr(
        policy,
        "_strategy_fit_without_castle",
        lambda state, action: (1.0, ("base evidence",)),
    )
    monkeypatch.setattr(strategy_hand_policy, "_castle_strategy_fit", lambda state, action: (0.0, ()))
    monkeypatch.setattr(
        strategy_hand_policy,
        "_burnt_strategy_fit",
        lambda state, action, hand_evaluator: (0.0, ()),
    )
    monkeypatch.setattr(strategy_hand_policy, "_dna_aces_fit", lambda policy, state, action: (0.0, ()))
    monkeypatch.setattr(strategy_hand_policy, "_play_repeats_hand", lambda policy, state, action: False)


def test_runner_target_hand_evidence_is_native_to_strategy_fit(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    _neutralize_other_strategy_evidence(monkeypatch, policy)
    state = SimpleNamespace(jokers=(RunnerJoker(),))
    action = BalatroAction(
        PLAY_CARDS,
        cards=[
            _card("10", "Hearts"),
            _card("9", "Clubs"),
            _card("8", "Diamonds"),
            _card("7", "Spades"),
            _card("6", "Hearts"),
        ],
    )

    value, rationale = policy._strategy_fit(state, action)

    assert value == 1.0 + target_hand_engine_policy.TARGET_HAND_FIT
    assert "base evidence" in rationale
    assert any("target-hand engine evidence: STRAIGHT" in note for note in rationale)


def test_runner_does_not_reward_non_target_play(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    _neutralize_other_strategy_evidence(monkeypatch, policy)
    state = SimpleNamespace(jokers=(RunnerJoker(),))
    action = BalatroAction(
        PLAY_CARDS,
        cards=[
            _card("10", "Hearts"),
            _card("10", "Clubs"),
        ],
    )

    value, rationale = policy._strategy_fit(state, action)

    assert value == 1.0
    assert "base evidence" in rationale
    assert not any("target-hand engine evidence" in note for note in rationale)


def test_target_hand_module_no_longer_installs_policy_wrapper():
    assert not hasattr(target_hand_engine_policy, "install_target_hand_engine_policy")
