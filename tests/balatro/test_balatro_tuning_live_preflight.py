from types import SimpleNamespace

import pytest

from games.balatro.tuning.live_preflight import validate_live_tuning_preflight


class _Observer:
    def __init__(self, snapshot):
        self.snapshot = snapshot
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def observe(self):
        return self.snapshot


class _Bridge:
    def __init__(self, status):
        self._status = status
    def status(self):
        return dict(self._status)


def _snapshot(*, phase="BLIND_SELECT", complete=True, deck="RED", stake="WHITE", ante=1):
    return SimpleNamespace(
        phase=phase,
        state_complete=complete,
        payload={"deck": deck, "stake": stake, "ante_num": ante},
    )


def _validate(snapshot=None, status=None, **kwargs):
    snapshot = snapshot or _snapshot()
    status = status or {
        "bridge": "1",
        "bridge_revision": "test",
        "achievement_gate": "UNSET",
    }
    return validate_live_tuning_preflight(
        expected_deck=kwargs.pop("expected_deck", "RED"),
        expected_stake=kwargs.pop("expected_stake", "WHITE"),
        observer_factory=lambda: _Observer(snapshot),
        bridge_factory=lambda: _Bridge(status),
        **kwargs,
    )


def test_preflight_accepts_fresh_settled_matching_boundary():
    result = _validate()
    assert result.phase == "BLIND_SELECT"
    assert result.state_complete is True
    assert result.deck == "RED"
    assert result.stake == "WHITE"
    assert result.ante == 1
    assert result.bridge_version == "1"
    assert result.bridge_revision == "test"
    assert result.achievement_gate == "UNSET"


def test_preflight_rejects_non_blind_select_phase_before_bridge_probe():
    called = []
    with pytest.raises(RuntimeError, match="fresh BLIND_SELECT"):
        validate_live_tuning_preflight(
            expected_deck="RED",
            expected_stake="WHITE",
            observer_factory=lambda: _Observer(_snapshot(phase="SHOP")),
            bridge_factory=lambda: called.append(True),
        )
    assert called == []


def test_preflight_rejects_unsettled_boundary():
    with pytest.raises(RuntimeError, match="not settled"):
        _validate(snapshot=_snapshot(complete=False))


def test_preflight_rejects_wrong_deck_or_stake():
    with pytest.raises(RuntimeError, match="deck/stake mismatch"):
        _validate(snapshot=_snapshot(deck="BLUE"))
    with pytest.raises(RuntimeError, match="deck/stake mismatch"):
        _validate(snapshot=_snapshot(stake="RED"))


def test_preflight_rejects_nonopening_ante_to_prevent_cross_trial_contamination():
    with pytest.raises(RuntimeError, match="fresh Ante 1"):
        _validate(snapshot=_snapshot(ante=2))


def test_preflight_rejects_incompatible_bridge_protocol():
    with pytest.raises(RuntimeError, match="protocol 1"):
        _validate(status={"bridge": "9", "achievement_gate": "UNSET"})


def test_preflight_rejects_disabled_or_unknown_achievement_gate():
    with pytest.raises(RuntimeError, match="achievement-disable gate is active"):
        _validate(status={"bridge": "1", "achievement_gate": "DISABLED"})
    with pytest.raises(RuntimeError, match="unavailable/unexpected"):
        _validate(status={"bridge": "1", "achievement_gate": "MYSTERY"})


def test_preflight_accepts_enabled_gate_representation():
    result = _validate(status={"bridge": "1", "achievement_gate": "ENABLED"})
    assert result.achievement_gate == "ENABLED"


def test_preflight_rejects_blank_expected_identity():
    with pytest.raises(ValueError, match="deck/stake identity"):
        _validate(expected_deck="")
