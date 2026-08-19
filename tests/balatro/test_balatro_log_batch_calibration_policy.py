from types import SimpleNamespace

from games.balatro.log_batch_calibration_policy import (
    _DEPENDENT_LEAF_CORES,
    _live_scaler_floor,
)
from games.balatro.strategy_multi_engine import SECONDARY, strategy_role


class BullJoker:
    pass


class BootstrapsJoker:
    pass


class GreenJoker:
    def __init__(self, mult=0):
        self.mult = mult


class RideTheBusJoker:
    def __init__(self, mult=0):
        self.mult = mult


class FlashCardJoker:
    def __init__(self, mult=0):
        self.mult = mult


def _state(*, money=0, jokers=()):
    return SimpleNamespace(money=money, jokers=list(jokers))


def test_cash_scalers_gain_large_live_retention_from_actual_cash():
    state = _state(money=254)
    bull_floor, bull_note = _live_scaler_floor(state, BullJoker())
    boots_floor, boots_note = _live_scaler_floor(state, BootstrapsJoker())

    assert bull_floor > 14.0
    assert boots_floor > 14.0
    assert "+508" in bull_note
    assert "+100" in boots_note


def test_accumulated_mult_scalers_become_harder_to_replace_as_they_scale():
    low, _ = _live_scaler_floor(_state(), GreenJoker(mult=2))
    high, _ = _live_scaler_floor(_state(), GreenJoker(mult=25))
    bus, _ = _live_scaler_floor(_state(), RideTheBusJoker(mult=20))
    flash, _ = _live_scaler_floor(_state(), FlashCardJoker(mult=18))

    assert high > low
    assert bus >= 10.0
    assert flash >= 10.0


def test_specialized_leaf_map_requires_defining_core_not_support_only():
    assert _DEPENDENT_LEAF_CORES["high_card_baron_mime"] == frozenset(
        {"baronjoker", "mimejoker"}
    )
    assert _DEPENDENT_LEAF_CORES["face_photochad"] == frozenset(
        {"photographjoker"}
    )
    assert _DEPENDENT_LEAF_CORES["face_pareidolia"] == frozenset(
        {"pareidoliajoker"}
    )


def test_cash_bull_bootstraps_remains_a_compatible_secondary_engine():
    assert strategy_role("cash_bull_bootstraps") == SECONDARY
