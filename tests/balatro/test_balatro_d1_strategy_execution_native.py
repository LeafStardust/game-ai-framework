from dataclasses import dataclass, field
from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.hand_action_policy import PACE_RECOVERY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
import games.balatro.live.strategy_hand_policy as strategy_hand_policy
import games.balatro.strategy_execution_guard_policy as strategy_execution_guard_policy


@dataclass(frozen=True)
class _Decision:
    action: object
    selected_plan: object
    pace_target: float = 100.0
    selected_immediate_score: float | None = None
    selected_pace_ratio: float | None = None
    selected_fallback_value: float | None = None
    setup_discard_consensus: bool = True
    confidence: float = 0.60
    rationale: tuple[str, ...] = ("baseline",)
    thresholds: object = field(
        default_factory=lambda: SimpleNamespace(
            safe_clear_probability_tolerance=0.05,
        )
    )
    mode: str = PACE_RECOVERY


def _plan(action, clear_probability: float):
    return SimpleNamespace(
        action=action,
        exact=True,
        value=SimpleNamespace(
            clear_probability=clear_probability,
            expected_progress=1.0,
            expected_hands_remaining=1.0,
            expected_discards_remaining=0.0,
            expected_score=50.0,
        ),
    )


def test_repetition_evidence_is_owned_by_strategy_policy(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
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
    monkeypatch.setattr(strategy_hand_policy, "_play_repeats_hand", lambda policy, state, action: True)

    action = BalatroAction(PLAY_CARDS, cards=[SimpleNamespace(rank="10", suit="Hearts")])
    value, rationale = policy._strategy_fit(SimpleNamespace(), action)

    assert value == 1.0 + strategy_execution_guard_policy.HAND_REPETITION_FIT
    assert "base evidence" in rationale
    assert any("realized hand_repetition evidence" in note for note in rationale)


def test_green_preservation_is_native_and_keeps_legacy_recovery_mode(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    play_action = BalatroAction(PLAY_CARDS, cards=[SimpleNamespace(rank="10", suit="Hearts")])
    discard_action = BalatroAction(DISCARD_CARDS, cards=[SimpleNamespace(rank="2", suit="Clubs")])
    play_plan = _plan(play_action, 0.92)
    discard_plan = _plan(discard_action, 0.95)
    decision = _Decision(action=discard_action, selected_plan=discard_plan)

    monkeypatch.setattr(
        strategy_hand_policy,
        "_green_preserving_play",
        lambda policy, state, plans, decision: play_plan,
    )
    monkeypatch.setattr(
        policy.evaluator,
        "project_play",
        lambda state, action: SimpleNamespace(expected_hand_score=50.0),
    )
    monkeypatch.setattr(policy.evaluator, "evaluate", lambda state, action: 7.0)

    result = policy._green_preserved_decision(
        SimpleNamespace(),
        (play_plan, discard_plan),
        decision,
    )

    assert result.action is play_action
    assert result.selected_plan is play_plan
    assert result.mode == PACE_RECOVERY
    assert result.setup_discard_consensus is False
    assert result.selected_immediate_score == 50.0
    assert result.selected_fallback_value == 7.0
    assert result.rationale[0].startswith("Green Joker preservation")


def test_strategy_execution_module_no_longer_installs_policy_wrapper():
    assert not hasattr(
        strategy_execution_guard_policy,
        "install_strategy_execution_guard_policy",
    )
    assert StrategyAwareLiveHandActionPolicy._strategy_fit.__module__ != (
        "games.balatro.strategy_execution_guard_policy"
    )
