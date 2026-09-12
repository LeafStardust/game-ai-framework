import pytest

from games.balatro.env.action_encoding import action_index
from games.balatro.env.actions import EnvAction
from games.balatro.env.random_baseline import (
    RANDOM_LEGAL_BASELINE_VERSION,
    RandomLegalBaselineError,
    RandomLegalStrategicBaseline,
)
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.state import BalatroState


def _frame(*, status=RunStatus.RUNNING, owner=TurnOwner.AGENT):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.owned_deck = state.deck.copy()
    state.phase = "SHOP"
    state.shop_active = True
    return EnvStateFrame(state, status=status, owner=owner)


def _actions():
    return (
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("REROLL_SHOP"),
    )


def test_env_b0_random_legal_sequence_is_reproducible_and_versioned():
    first = RandomLegalStrategicBaseline("EVAL-17")
    second = RandomLegalStrategicBaseline("EVAL-17")
    first_decisions = [first.select(_frame(), _actions()) for _ in range(12)]
    second_decisions = [second.select(_frame(), _actions()) for _ in range(12)]
    assert first_decisions == second_decisions
    assert all(item.baseline_version == RANDOM_LEGAL_BASELINE_VERSION for item in first_decisions)
    assert [item.decision_number for item in first_decisions] == list(range(12))


def test_env_b0_random_baseline_never_selects_a_masked_action():
    policy = RandomLegalStrategicBaseline(9)
    legal = _actions()
    legal_indices = {action_index(action) for action in legal}
    decisions = [policy.select(_frame(), legal) for _ in range(100)]
    assert {item.action_index for item in decisions}.issubset(legal_indices)
    assert all(item.action in legal for item in decisions)


def test_env_b0_selection_does_not_mutate_frame_or_legal_actions():
    frame = _frame()
    actions = _actions()
    before_deck = tuple(frame.state.deck)
    decision = RandomLegalStrategicBaseline("ISOLATED").select(frame, actions)
    assert tuple(frame.state.deck) == before_deck
    assert actions == _actions()
    assert decision.action == actions[2]


def test_env_b0_sampling_is_independent_of_backend_action_enumeration_order():
    first = RandomLegalStrategicBaseline("ORDER")
    second = RandomLegalStrategicBaseline("ORDER")
    assert first.select(_frame(), _actions()) == second.select(_frame(), reversed(_actions()))


def test_env_b0_terminal_empty_mask_returns_no_decision():
    frame = _frame(status=RunStatus.LOSS, owner=TurnOwner.TERMINAL)
    policy = RandomLegalStrategicBaseline("TERMINAL")
    assert policy.select(frame, ()) is None
    assert policy.decision_number == 0


def test_env_b0_empty_nonterminal_mask_fails_closed_without_rescue():
    with pytest.raises(RandomLegalBaselineError, match="empty legal action mask"):
        RandomLegalStrategicBaseline("EMPTY").select(_frame(), ())


def test_env_b0_non_agent_and_terminal_actions_fail_closed():
    policy = RandomLegalStrategicBaseline("OWNER")
    with pytest.raises(RandomLegalBaselineError, match="agent-owned"):
        policy.select(_frame(owner=TurnOwner.ENVIRONMENT), _actions())
    with pytest.raises(RandomLegalBaselineError, match="terminal frame"):
        policy.select(_frame(status=RunStatus.LOSS, owner=TurnOwner.TERMINAL), _actions())


@pytest.mark.parametrize("seed", [True, 1.5, None])
def test_env_b0_invalid_baseline_seed_fails_closed(seed):
    with pytest.raises(TypeError, match="baseline seed"):
        RandomLegalStrategicBaseline(seed)
