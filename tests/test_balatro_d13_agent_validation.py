from types import SimpleNamespace

from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.d13_agent_validation import D13ValidationState


def _snapshot(*, ante=2, phase="BLIND_SELECT", blind_type="SMALL", tag="tag_rare", sequence=1):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={
            "deck": "RED",
            "stake": "WHITE",
            "ante_num": ante,
            "blind": {
                "type": blind_type,
                "tag": tag,
            },
        },
    )


def _decision(*, action="SELECT_BLIND", source="D13 contextual blind play-vs-skip policy", ante=2):
    return SimpleNamespace(
        snapshot=_snapshot(ante=ante),
        action=SimpleNamespace(name=action),
        source=source,
        notes=("skip_margin=3.0",),
        decision_diagnostics={"layer": "D13", "selected": {"margin": 3.0}},
    )


def _result(*, ante=2, phase="ROUND", sequence=2):
    return SimpleNamespace(
        after=_snapshot(
            ante=ante,
            phase=phase,
            sequence=sequence,
        )
    )


def test_validation_continues_after_non_skip_before_ante_limit():
    state = D13ValidationState(stop_before_ante=5)

    state.capture(_decision(action="SELECT_BLIND"), _result(ante=2))

    assert state.stop_requested() is False
    assert state.skip_evidence is None
    assert state.ante_limit_reached is False


def test_validation_stops_immediately_after_real_d13_skip():
    state = D13ValidationState(stop_before_ante=5)

    state.capture(_decision(action="SKIP_BLIND"), _result(ante=2, phase="SHOP"))

    assert state.stop_requested() is True
    assert state.skip_evidence is not None
    assert state.skip_evidence["action"] == "SKIP_BLIND"
    assert state.skip_evidence["ante"] == 2
    assert state.skip_evidence["diagnostics"]["layer"] == "D13"
    assert state.ante_limit_reached is False


def test_non_d13_skip_does_not_count_as_validation_evidence():
    state = D13ValidationState(stop_before_ante=5)

    state.capture(
        _decision(action="SKIP_BLIND", source="legacy fallback"),
        _result(ante=2),
    )

    assert state.stop_requested() is False
    assert state.skip_evidence is None


def test_validation_stops_before_ante_five_without_fake_skip_evidence():
    state = D13ValidationState(stop_before_ante=5)

    state.capture(_decision(action="SELECT_BLIND", ante=4), _result(ante=5))

    assert state.stop_requested() is True
    assert state.ante_limit_reached is True
    assert state.skip_evidence is None
