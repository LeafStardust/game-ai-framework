from types import SimpleNamespace

from games.balatro.actions import BUY_BOOSTER, BalatroAction
from games.balatro.early_spend_sanity_policy import (
    EARLY_HARD_CASH_FLOOR,
    _cash_floor_safe,
)
from games.balatro.shop_booster_policy import HOLD, BuildAwareShopBoosterPolicy
from games.balatro.shop_voucher_policy import VoucherAcquisitionPolicy


class _Profiler:
    def __init__(self, profile):
        self._profile = profile

    def profile(self, state):
        return self._profile


def _profile(*, ante=2, jokers=1, invested=False, free_joker_slots=4):
    return SimpleNamespace(
        ante=ante,
        joker_names=tuple(f"Joker {i}" for i in range(jokers)),
        hand_levels=(("PAIR", 2 if invested else 1),),
        joker_slots=5,
        free_joker_slots=free_joker_slots,
    )


def test_structural_voucher_cannot_spend_early_run_from_11_to_1():
    profile = _profile(ante=2, jokers=1)
    allowed, rationale = VoucherAcquisitionPolicy._early_survival_gate(
        SimpleNamespace(),
        profile,
        "Paint Brush",
        price=10,
        money_after=1,
    )

    assert allowed is False
    assert any("hard early cash-floor hold" in note for note in rationale)


def test_structural_voucher_can_keep_explicit_exception_at_14_to_4():
    profile = _profile(ante=2, jokers=1)
    allowed, rationale = VoucherAcquisitionPolicy._early_survival_gate(
        SimpleNamespace(),
        profile,
        "Paint Brush",
        price=10,
        money_after=4,
    )

    assert allowed is True
    assert any("early structural exception=Paint Brush" in note for note in rationale)


def test_antimatter_keeps_weighted_reserve_authority_even_at_zero_cash():
    profile = _profile(ante=1, jokers=0)
    allowed, rationale = VoucherAcquisitionPolicy._early_survival_gate(
        SimpleNamespace(),
        profile,
        "Antimatter",
        price=10,
        money_after=0,
    )

    assert allowed is True
    assert any("weighted-reserve authority" in note for note in rationale)


def test_fragile_early_build_requires_five_dollars_after_optional_spend():
    profile = _profile(ante=2, jokers=1)

    assert _cash_floor_safe(profile, EARLY_HARD_CASH_FLOOR)
    assert not _cash_floor_safe(profile, EARLY_HARD_CASH_FLOOR - 1)


def test_established_build_is_not_bound_by_early_cash_floor():
    assert _cash_floor_safe(_profile(ante=2, jokers=3), 1)
    assert _cash_floor_safe(_profile(ante=2, jokers=1, invested=True), 1)
    assert _cash_floor_safe(_profile(ante=3, jokers=1), 1)


def test_buffoon_pack_cannot_spend_fragile_early_run_from_5_to_1():
    profile = _profile(ante=2, jokers=1, free_joker_slots=4)
    policy = BuildAwareShopBoosterPolicy(build_profiler=_Profiler(profile))
    state = SimpleNamespace(
        phase="SHOP",
        money=5,
        vouchers=(),
        jokers=(object(),),
    )
    action = BalatroAction(
        BUY_BOOSTER,
        target=SimpleNamespace(label="Buffoon Pack", price=4),
    )

    recommendation = policy.recommend(state, action)

    assert recommendation.decision == HOLD
    assert any("hard early cash-floor hold" in note for note in recommendation.rationale)


def test_buffoon_pack_cannot_spend_fragile_early_run_from_4_to_0():
    profile = _profile(ante=2, jokers=1, free_joker_slots=4)
    policy = BuildAwareShopBoosterPolicy(build_profiler=_Profiler(profile))
    state = SimpleNamespace(
        phase="SHOP",
        money=4,
        vouchers=(),
        jokers=(object(),),
    )
    action = BalatroAction(
        BUY_BOOSTER,
        target=SimpleNamespace(label="Buffoon Pack", price=4),
    )

    recommendation = policy.recommend(state, action)

    assert recommendation.decision == HOLD
