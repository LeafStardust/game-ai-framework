import pytest

from games.balatro.actions import BalatroAction
from games.balatro.env.actions import EnvAction
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.symbolic_baseline import (
    SYMBOLIC_HEADLESS_BASELINE_VERSION,
    DeterministicSymbolicHeadlessBaseline,
    SymbolicHeadlessBaselineError,
)
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.state import BalatroState


def _frame(*, status=RunStatus.RUNNING, owner=TurnOwner.AGENT):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.owned_deck = state.deck.copy()
    state.phase = "SHOP"
    state.shop_active = True
    joker = FlatMultJoker()
    joker.center = "j_joker"
    joker.price = 2
    joker.edition = None
    state.shop_jokers = [joker]
    return EnvStateFrame(state, status=status, owner=owner)


def test_env_b0_existing_shop_policy_maps_exact_end_shop_action():
    policy = BalatroShopPolicy()
    baseline = DeterministicSymbolicHeadlessBaseline(
        lambda state, actions: policy.choose_action(state, list(actions))
    )
    decision = baseline.select(_frame(), (EnvAction.from_alias("END_SHOP"),))
    assert decision.baseline_version == SYMBOLIC_HEADLESS_BASELINE_VERSION
    assert decision.action == EnvAction.from_alias("END_SHOP")


def test_env_b0_symbolic_target_maps_back_to_exact_legal_slot():
    legal = (
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
    )
    baseline = DeterministicSymbolicHeadlessBaseline(
        lambda state, actions: actions[1]
    )
    assert baseline.select(_frame(), legal).action == legal[1]


def test_env_b0_symbolic_policy_receives_isolated_public_state():
    frame = _frame()
    frame.state.deck[0].live_id = 101
    frame.state.owned_deck[0].live_id = 101
    frame.state.shop_jokers[0].live_id = 202
    frame.state.shop_jokers[0].area_index = 0
    original_money = frame.state.money

    def mutate_copy(state, actions):
        assert len(state.deck) == 52
        assert set(state.deck) == {None}
        assert state.owned_deck[0].live_id is None
        assert state.shop_jokers[0].live_id is None
        assert state.shop_jokers[0].area_index is None
        state.money = 999
        state.shop_jokers[0].price = 999
        return actions[0]

    decision = DeterministicSymbolicHeadlessBaseline(mutate_copy).select(
        frame, (EnvAction.from_alias("BUY_JOKER", {"slot": 0}),)
    )
    assert decision.action.alias == "BUY_JOKER"
    assert frame.state.money == original_money
    assert frame.state.shop_jokers[0].price == 2


def test_env_b0_ambiguous_or_non_candidate_symbolic_output_fails_closed():
    legal = (EnvAction.from_alias("END_SHOP"),)
    baseline = DeterministicSymbolicHeadlessBaseline(
        lambda state, actions: BalatroAction("REFRESH_SHOP")
    )
    with pytest.raises(SymbolicHeadlessBaselineError, match="exactly one legal candidate"):
        baseline.select(_frame(), legal)


def test_env_b0_pack_choice_mapping_remains_fail_closed_without_public_objects():
    legal = (EnvAction.from_alias("CHOOSE_PACK_OPTION", {"option_index": 0}),)
    with pytest.raises(SymbolicHeadlessBaselineError, match="pack-choice objects"):
        DeterministicSymbolicHeadlessBaseline(lambda state, actions: actions[0]).select(
            _frame(), legal
        )


def test_env_b0_empty_nonterminal_and_nonagent_calls_fail_closed():
    baseline = DeterministicSymbolicHeadlessBaseline(lambda state, actions: actions[0])
    with pytest.raises(SymbolicHeadlessBaselineError, match="empty legal action mask"):
        baseline.select(_frame(), ())
    with pytest.raises(SymbolicHeadlessBaselineError, match="agent-owned"):
        baseline.select(_frame(owner=TurnOwner.ENVIRONMENT), ())


def test_env_b0_terminal_empty_actions_returns_none():
    baseline = DeterministicSymbolicHeadlessBaseline(lambda state, actions: actions[0])
    terminal = _frame(status=RunStatus.LOSS, owner=TurnOwner.TERMINAL)
    assert baseline.select(terminal, ()) is None


def test_env_b0_invalid_decider_fails_closed():
    with pytest.raises(TypeError, match="decider"):
        DeterministicSymbolicHeadlessBaseline(None)
