from types import SimpleNamespace

from games.balatro.shop_voucher_policy import (
    BUY,
    HOLD,
    VoucherAcquisitionPolicy,
    VoucherAcquisitionThresholds,
)


class _Estimator:
    def __init__(self, value: float):
        self.value = float(value)

    def estimate(self, state, action):
        return self.value, ("synthetic persistent value",)


class _Profiler:
    def __init__(self, *, ante: int, money: int, joker_names=(), hand_levels=()):
        self.result = SimpleNamespace(
            ante=ante,
            money=money,
            joker_names=tuple(joker_names),
            hand_levels=tuple(hand_levels),
            free_joker_slots=max(0, 5 - len(tuple(joker_names))),
        )

    def profile(self, state):
        return self.result


class _ResourceValuator:
    def __init__(self, *, horizon: float = 1.2, total_cost: float = 2.0):
        self.horizon = float(horizon)
        self.total_cost = float(total_cost)

    def horizon_value(self, state, *, target_ante, weight):
        return SimpleNamespace(total=self.horizon)

    def money_spend_cost(self, **kwargs):
        return SimpleNamespace(
            direct=self.total_cost,
            interest=0.0,
            reserve=0.0,
            total=self.total_cost,
        )


def _state(*, money: int, jokers=(), consumables=(), plays=None):
    return SimpleNamespace(
        phase="SHOP",
        money=money,
        jokers=list(jokers),
        vouchers=[],
        consumables=list(consumables),
        hand_play_counts=plays or {},
        hand_size=8,
    )


def _candidate(label: str, *, price: int = 10):
    return SimpleNamespace(label=label, price=price)


def _policy(
    *,
    ante: int,
    money: int,
    joker_names=(),
    hand_levels=(),
    base_value: float = 5.5,
    total_cost: float = 2.0,
):
    return VoucherAcquisitionPolicy(
        VoucherAcquisitionThresholds(minimum_money_after=0),
        item_value_estimator=_Estimator(base_value),
        profiler=_Profiler(
            ante=ante,
            money=money,
            joker_names=joker_names,
            hand_levels=hand_levels,
        ),
        resource_valuator=_ResourceValuator(total_cost=total_cost),
    )


def test_early_expensive_utility_voucher_cannot_crowd_out_scoring_capital():
    policy = _policy(
        ante=2,
        money=14,
        joker_names=("Mr. Bones",),
        base_value=5.5,
    )

    decision = policy.decide(_state(money=14), _candidate("Wasteful"))

    assert decision.action == HOLD
    assert decision.money_after == 4
    assert any("early survival hold" in note for note in decision.rationale)


def test_early_structural_capacity_voucher_keeps_explicit_exception():
    policy = _policy(
        ante=2,
        money=14,
        joker_names=("Mr. Bones",),
        base_value=5.5,
    )

    decision = policy.decide(_state(money=14), _candidate("Paint Brush"))

    assert decision.action == BUY
    assert any("early structural exception=Paint Brush" in note for note in decision.rationale)


def test_early_voucher_can_compete_after_scoring_readiness_is_established():
    policy = _policy(
        ante=2,
        money=14,
        joker_names=("A", "B", "C"),
        base_value=5.5,
    )

    decision = policy.decide(_state(money=14), _candidate("Wasteful"))

    assert decision.action == BUY
    assert any("early readiness jokers=3" in note for note in decision.rationale)


def test_observatory_without_planet_infrastructure_is_not_generic_persistent_value():
    policy = _policy(
        ante=4,
        money=23,
        joker_names=("A", "B", "C", "D"),
        base_value=7.0,
        total_cost=4.0,
    )

    decision = policy.decide(_state(money=23), _candidate("Observatory"))

    assert decision.action == HOLD
    assert decision.build_compatibility == -4.0
    assert any("held_planet=False perkeo=False" in note for note in decision.rationale)


def test_telescope_requires_realized_hand_repetition_for_positive_compatibility():
    policy = _policy(
        ante=3,
        money=30,
        joker_names=("A", "B", "C"),
        base_value=3.0,
        total_cost=3.0,
    )

    weak = policy.decide(
        _state(money=30, plays={"PAIR": 2}),
        _candidate("Telescope"),
    )
    established = policy.decide(
        _state(money=30, plays={"PAIR": 6}),
        _candidate("Telescope"),
    )

    assert weak.build_compatibility == -1.5
    assert established.build_compatibility == 1.0
    assert established.total_advantage > weak.total_advantage
