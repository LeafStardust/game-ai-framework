from games.balatro.env import (
    BALATRO_ENV_VERSION,
    BackendStep,
    BalatroHeadlessEnvironment,
    EnvAction,
    EnvStateFrame,
    RunStatus,
    TurnOwner,
)
from games.balatro.env_contract import contract_for, training_action_contracts
from games.balatro.state import BalatroState


class _FakeBackend:
    def __init__(self):
        self.seed = None
        self.frame = None
        self.actions = (EnvAction.from_alias("END_SHOP"),)

    def reset(self, seed):
        self.seed = seed
        state = BalatroState()
        state.phase = "SHOP"
        self.frame = EnvStateFrame(state=state, info={"seed": seed})
        return self.frame

    def step(self, action):
        assert action in self.actions
        state = self.frame.state.copy()
        state.phase = "ROUND_START"
        self.frame = EnvStateFrame(
            state=state,
            status=RunStatus.ANTE_8_WIN,
            owner=TurnOwner.TERMINAL,
            info={"action": action.alias},
        )
        return BackendStep(frame=self.frame, reward=1.0)

    def legal_actions(self):
        return self.actions

    def serialize(self):
        return {"seed": self.seed, "phase": self.frame.state.phase}

    def restore(self, payload):
        state = BalatroState()
        state.phase = payload["phase"]
        self.frame = EnvStateFrame(state=state, info={"restored": True})
        return self.frame


def test_balatro_env_r0_has_explicit_version():
    assert BALATRO_ENV_VERSION == "r0-v1"


def test_balatro_env_r0_actions_alias_frozen_contract_ids():
    for contract in training_action_contracts():
        action = EnvAction.from_alias(contract.alias)
        assert action.action_id == contract.action_id
        assert contract_for(action.alias) is contract


def test_balatro_env_r0_rejects_non_training_action():
    try:
        EnvAction.from_alias("REROLL_SHOP")
    except ValueError as exc:
        assert "not training-exposed" in str(exc)
    else:
        raise AssertionError("planned action leaked into R0 training surface")


def test_balatro_env_r0_wraps_canonical_state_without_aliasing_observation():
    backend = _FakeBackend()
    env = BalatroHeadlessEnvironment(backend)
    obs, info = env.reset(seed="seed-a")

    assert isinstance(obs, BalatroState)
    assert obs is not backend.frame.state
    assert obs.phase == "SHOP"
    assert info == {"seed": "seed-a"}

    obs.money = 999
    assert backend.frame.state.money == 0


def test_balatro_env_r0_legal_actions_fail_closed_to_contract():
    backend = _FakeBackend()
    env = BalatroHeadlessEnvironment(backend)
    env.reset(seed=1)
    assert env.legal_actions() == (EnvAction.from_alias("END_SHOP"),)

    backend.actions = (EnvAction(alias="REROLL_SHOP"),)
    try:
        env.legal_actions()
    except ValueError as exc:
        assert "non-training action" in str(exc)
    else:
        raise AssertionError("backend exposed a planned action")


def test_balatro_env_r0_step_uses_gym_signature_and_terminal_semantics():
    backend = _FakeBackend()
    env = BalatroHeadlessEnvironment(backend)
    env.reset(seed=7)

    obs, reward, terminated, truncated, info = env.step(EnvAction.from_alias("END_SHOP"))
    assert isinstance(obs, BalatroState)
    assert reward == 1.0
    assert terminated is True
    assert truncated is False
    assert info == {"action": "END_SHOP"}
    assert env.legal_actions() == ()

    try:
        env.step(EnvAction.from_alias("END_SHOP"))
    except RuntimeError as exc:
        assert "terminal" in str(exc)
    else:
        raise AssertionError("terminal environment accepted another action")


def test_balatro_env_r0_rejects_action_not_in_current_legal_set():
    backend = _FakeBackend()
    env = BalatroHeadlessEnvironment(backend)
    env.reset(seed=9)

    try:
        env.step(EnvAction.from_alias("BUY_JOKER", {"slot": 0}))
    except ValueError as exc:
        assert "illegal action" in str(exc)
    else:
        raise AssertionError("environment accepted an action outside backend legality")


def test_balatro_env_r0_turn_ownership_blocks_agent_actions():
    backend = _FakeBackend()
    env = BalatroHeadlessEnvironment(backend)
    env.reset(seed=3)
    backend.frame = EnvStateFrame(state=backend.frame.state, owner=TurnOwner.TACTICAL_POLICY)
    env._frame = backend.frame

    assert env.legal_actions() == ()
    try:
        env.step(EnvAction.from_alias("END_SHOP"))
    except RuntimeError as exc:
        assert "turn owner" in str(exc)
    else:
        raise AssertionError("agent acted during tactical-policy ownership")


def test_balatro_env_r0_frame_enforces_terminal_owner_consistency():
    state = BalatroState()
    try:
        EnvStateFrame(state=state, status=RunStatus.LOSS, owner=TurnOwner.AGENT)
    except ValueError as exc:
        assert "terminal frame" in str(exc)
    else:
        raise AssertionError("terminal frame accepted non-terminal owner")


def test_balatro_env_r0_serialization_boundary_delegates_to_backend():
    backend = _FakeBackend()
    env = BalatroHeadlessEnvironment(backend)
    env.reset(seed="replay-seed")
    payload = env.serialize()
    assert payload == {"seed": "replay-seed", "phase": "SHOP"}

    obs, info = env.restore({"seed": "replay-seed", "phase": "SHOP"})
    assert obs.phase == "SHOP"
    assert info == {"restored": True}
