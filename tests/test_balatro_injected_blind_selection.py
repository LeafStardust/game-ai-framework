from __future__ import annotations

import pytest

from games.balatro.actions import SELECT_BLIND, SKIP_BLIND, BalatroAction
from games.balatro.live.injected import FirstPartyBalatroBridge
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
    UnsupportedInjectedAction,
)
from games.balatro.live.injected.install import asset_dir
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(
    sequence: int,
    phase: str,
    *,
    state_complete: bool = True,
    blind_type: str | None = None,
    blind_tag: str | None = None,
):
    payload = {}
    if blind_type is not None or blind_tag is not None:
        payload["blind"] = {}
        if blind_type is not None:
            payload["blind"]["type"] = blind_type
        if blind_tag is not None:
            payload["blind"]["tag"] = blind_tag
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=state_complete,
        payload=payload,
    )


class FakeObserver:
    def __init__(self, *snapshots):
        self.snapshots = list(snapshots)

    def observe(self):
        return self.snapshots.pop(0)


class FakeBridge:
    def __init__(self):
        self.calls = []

    def select_blind(self):
        self.calls.append(("select_blind",))

    def skip_blind(self):
        self.calls.append(("skip_blind",))


def test_bridge_select_blind_uses_expected_wire_command(monkeypatch, tmp_path):
    bridge = FirstPartyBalatroBridge(tmp_path)
    calls = []

    monkeypatch.setattr(
        bridge,
        "_call",
        lambda action, indices=(): calls.append((action, tuple(indices))) or "accepted",
    )

    bridge.select_blind()

    assert calls == [("SELECT_BLIND", ())]


def test_bridge_asset_invokes_native_select_blind_callback():
    source = (asset_dir() / "bridge.lua").read_text(encoding="utf-8")

    assert 'require_state("BLIND_SELECT")' in source
    assert 'get_UIE_by_ID("select_blind_button")' in source
    assert "G.FUNCS and G.FUNCS.select_blind" in source
    assert 'action == "SELECT_BLIND"' in source


def test_injected_dispatcher_select_blind_waits_for_settled_hand_state():
    before = _snapshot(1, "BLIND_SELECT")
    transient = _snapshot(2, "BLIND_SELECT", state_complete=False)
    after = _snapshot(3, "SELECTING_HAND")
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(transient, after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(BalatroAction(SELECT_BLIND), snapshot=before)

    assert bridge.calls == [("select_blind",)]
    assert result.after is after


def test_injected_dispatcher_rejects_select_blind_outside_blind_select():
    before = _snapshot(1, "SHOP")
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(),
        bridge=bridge,
        poll_interval=0,
    )

    with pytest.raises(UnsupportedInjectedAction, match="BLIND_SELECT"):
        dispatcher.dispatch(BalatroAction(SELECT_BLIND), snapshot=before)

    assert bridge.calls == []


@pytest.mark.parametrize(
    ("before_blind", "wrong_blind", "expected_blind"),
    [
        ("SMALL", "BOSS", "BIG"),
        ("BIG", "SMALL", "BOSS"),
    ],
)
def test_injected_dispatcher_skip_blind_waits_for_exact_next_blind(
    before_blind,
    wrong_blind,
    expected_blind,
):
    before = _snapshot(10, "BLIND_SELECT", blind_type=before_blind)
    wrong = _snapshot(11, "BLIND_SELECT", blind_type=wrong_blind)
    after = _snapshot(12, "BLIND_SELECT", blind_type=expected_blind)
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(wrong, after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(BalatroAction(SKIP_BLIND), snapshot=before)

    assert bridge.calls == [("skip_blind",)]
    assert result.after is after
    assert result.details["blind_before"] == before_blind
    assert result.details["blind_after"] == expected_blind


@pytest.mark.parametrize(
    ("blind_tag", "pack_phase"),
    [
        ("tag_standard", "STANDARD_PACK"),
        ("tag_ethereal", "SPECTRAL_PACK"),
    ],
)
def test_injected_dispatcher_skip_blind_accepts_matching_tag_pack_phase(
    blind_tag,
    pack_phase,
):
    before = _snapshot(
        30,
        "BLIND_SELECT",
        blind_type="SMALL",
        blind_tag=blind_tag,
    )
    after = _snapshot(31, pack_phase, blind_type="BIG")
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(BalatroAction(SKIP_BLIND), snapshot=before)

    assert bridge.calls == [("skip_blind",)]
    assert result.after is after
    assert result.after.phase == pack_phase
    assert result.details["blind_before"] == "SMALL"
    assert result.details["blind_after"] == "BIG"


def test_injected_dispatcher_skip_blind_rejects_unrelated_pack_phase():
    before = _snapshot(
        40,
        "BLIND_SELECT",
        blind_type="SMALL",
        blind_tag="tag_standard",
    )
    wrong_pack = _snapshot(41, "SPECTRAL_PACK", blind_type="BIG")
    after = _snapshot(42, "STANDARD_PACK", blind_type="BIG")
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(wrong_pack, after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(BalatroAction(SKIP_BLIND), snapshot=before)

    assert bridge.calls == [("skip_blind",)]
    assert result.after is after


def test_injected_dispatcher_rejects_boss_blind_skip_before_bridge_call():
    before = _snapshot(20, "BLIND_SELECT", blind_type="BOSS")
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(),
        bridge=bridge,
        poll_interval=0,
    )

    with pytest.raises(UnsupportedInjectedAction, match="Small/Big blind"):
        dispatcher.dispatch(BalatroAction(SKIP_BLIND), snapshot=before)

    assert bridge.calls == []
