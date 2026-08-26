from types import SimpleNamespace

import games.balatro.build_health_policy as build_health_policy
import games.balatro.shop_clear_probability_health_policy as clear_health
from games.balatro.build_health_policy import PlaybookBuildHealthShopArbiter
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.shop_runtime_contract_policy import install_shop_runtime_contract_policy


class _Score:
    total = 1.0


class _FakeScorer:
    def score(self, *args, **kwargs):
        return _Score()


class _RecordingHealth:
    def __init__(self):
        self.seen = None

    def evaluate(self, state):
        self.seen = state
        return "health"


def test_internal_build_health_projection_never_launches_bounded_d1(monkeypatch):
    clear_health.install_shop_clear_probability_health_policy()

    def unexpected_d1(*args, **kwargs):
        raise AssertionError("hypothetical D2/D14 Build Health launched nested D1")

    monkeypatch.setattr(clear_health, "bounded_shop_clear_probability", unexpected_d1)
    evaluator = RuntimeBuildHealthEvaluator(scorer=_FakeScorer())
    state = SimpleNamespace(
        phase="SHOP",
        blind_score=300,
        blind_requirement=300,
        blind=None,
        score=0,
        hands_remaining=4,
        hand_size=8,
        owned_deck=(),
        deck=(),
        jokers=(),
        _rw_internal_build_health_projection=True,
    )

    survival, immediate = evaluator._survival_and_immediate(state)

    assert 0.0 <= survival <= 1.0
    assert 0.0 <= immediate <= 1.0


def test_projected_health_marks_internal_candidate_state(monkeypatch):
    install_shop_runtime_contract_policy()
    recorder = _RecordingHealth()
    monkeypatch.setattr(build_health_policy, "_HEALTH", recorder)
    state = SimpleNamespace(phase="SHOP", jokers=[], money=10)

    result = build_health_policy._projected_health(state, [])

    assert result == "health"
    assert recorder.seen is not state
    assert recorder.seen._rw_internal_build_health_projection is True


def test_legacy_named_bundle_planner_cannot_reopen_canonical_shop_arbitration():
    install_shop_runtime_contract_policy()
    sentinel = object()

    result = PlaybookBuildHealthShopArbiter._bundle_decision(
        object(),
        SimpleNamespace(phase="SHOP"),
        sentinel,
    )

    assert result is sentinel
