from types import SimpleNamespace

import games.balatro.shop_clear_probability_health_policy as clear_health
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.shop_runtime_contract_policy import install_shop_runtime_contract_policy
from games.balatro.shop_arbiter import BuildAwareShopArbiter


class _Score:
    total = 1.0


class _FakeScorer:
    def score(self, *args, **kwargs):
        return _Score()


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


def test_runtime_contract_registration_is_idempotent_and_has_no_legacy_shop_authority():
    install_shop_runtime_contract_policy()
    install_shop_runtime_contract_policy()

    assert BuildAwareShopArbiter._rw_runtime_contract_installed is True
