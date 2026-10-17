from copy import deepcopy
import json
import subprocess
import sys
import time

import pytest

from games.mahjong_soul.live.runtime.manual_discard import ManualDiscardSession
from tests.mahjong_soul.test_controller import confirmed
from tests.mahjong_soul.test_input import inputs, Mouse


def setup(tmp_path, **kwargs):
    report, profile = inputs()
    mouse = Mouse()
    session = ManualDiscardSession(mouse, profile, 0, "0p", tmp_path / "ticket.json", **kwargs)
    return report, mouse, session


def approve(session):
    session.ticket.write_text(json.dumps({"token": session.plan.token, "tile": session.tile}), encoding="utf-8")


def test_whole_session_retains_controller_across_long_review_and_exact_ack(tmp_path):
    report, mouse, session = setup(tmp_path)
    selection = session.start(report, fresh=True, now=10)
    original = session.controller
    assert selection["selection_sent"] and len(mouse.clicks) == 1
    assert session.tick(report, fresh=True, now=150) == {"phase": "review"}
    approve(session)
    assert session.tick(report, fresh=True, now=151)["confirmation_sent"]
    assert session.controller is original and len(mouse.clicks) == 2
    assert session.tick(report, [("other", confirmed())], fresh=True, now=152) == {"phase": "server"}
    assert session.tick(report, [("game", dict(confirmed(), source="restore"))], fresh=True, now=153) == {"phase": "server"}
    result = session.tick(report, [("game", confirmed())], fresh=True, now=154)
    assert result["confirmed"] and session.phase == "complete"
    session.tick(report, fresh=True, now=160)
    assert len(mouse.clicks) == 2
    with pytest.raises(ValueError, match="already"):
        session.start(report, fresh=True, now=160)


@pytest.mark.parametrize("failure", ["board", "closed", "incomplete", "manual_discard", "timeout"])
def test_changes_during_review_never_send_second_click_or_allow_retry(tmp_path, failure):
    report, mouse, session = setup(tmp_path)
    session.start(report, fresh=True, now=10)
    approve(session)
    changed = deepcopy(report); events = []; now = 11
    if failure == "board": changed["state"]["step"] += 1
    if failure == "closed": changed["connection_open"] = False
    if failure == "incomplete": changed["state_ready"] = False
    if failure == "manual_discard": events = [("game", confirmed())]
    if failure == "timeout": now = 305
    with pytest.raises(ValueError): session.tick(changed, events, fresh=True, now=now)
    assert session.phase == "failed" and len(mouse.clicks) == 1
    with pytest.raises(ValueError): session.tick(report, fresh=True, now=now)
    with pytest.raises(ValueError): session.start(report, fresh=True, now=now)
    assert len(mouse.clicks) == 1


def test_ticket_must_be_exact_and_capture_fresh_before_confirmation(tmp_path):
    report, mouse, session = setup(tmp_path)
    session.start(report, fresh=True, now=10)
    session.ticket.write_text("{", encoding="utf-8")
    session.tick(report, fresh=True, now=11)
    session.ticket.write_text(json.dumps({"token": "old", "tile": "0p"}), encoding="utf-8")
    session.tick(report, fresh=True, now=12)
    approve(session)
    session.tick(report, fresh=False, now=13)
    assert len(mouse.clicks) == 1
    session.tick(report, fresh=True, now=14)
    assert len(mouse.clicks) == 2
    # Ticket left in place must never send additional input.
    session.tick(report, fresh=True, now=15)
    assert len(mouse.clicks) == 2


@pytest.mark.parametrize("failure", ["stale", "existing_ticket", "backend"])
def test_preflight_or_delivery_failure_cannot_restart_session(tmp_path, failure):
    report, mouse, session = setup(tmp_path)
    if failure == "existing_ticket": session.ticket.write_text("{}", encoding="utf-8")
    if failure == "backend":
        def fail(*args):
            mouse.clicks.append(args)
            raise OSError("uncertain delivery")
        mouse.click = fail
    with pytest.raises((ValueError, OSError)):
        session.start(report, fresh=failure != "stale", now=10)
    with pytest.raises(ValueError): session.start(report, fresh=True, now=11)
    assert len(mouse.clicks) == (1 if failure == "backend" else 0)


def test_second_click_delivery_failure_is_terminal(tmp_path):
    report, mouse, session = setup(tmp_path)
    session.start(report, fresh=True, now=10)
    approve(session)
    def fail(*args):
        mouse.clicks.append(args)
        raise OSError("uncertain delivery")
    mouse.click = fail
    with pytest.raises(OSError): session.tick(report, fresh=True, now=11)
    with pytest.raises(ValueError): session.tick(report, fresh=True, now=12)
    assert len(mouse.clicks) == 2


def test_missing_server_ack_never_retries(tmp_path):
    report, mouse, session = setup(tmp_path)
    session.start(report, fresh=True, now=10)
    approve(session)
    session.tick(report, fresh=True, now=11)
    with pytest.raises(ValueError): session.tick(report, fresh=True, now=16)
    assert len(mouse.clicks) == 2 and session.phase == "failed"


def test_process_survives_closed_stdin_and_receives_ticket_from_another_process(tmp_path):
    # Exercise the transport that failed live, using a fake mouse only.
    script = r"""
import json,sys,time
from pathlib import Path
from games.mahjong_soul.live.runtime.manual_discard import ManualDiscardSession
from tests.mahjong_soul.test_input import inputs,Mouse
from tests.mahjong_soul.test_controller import confirmed
report,profile=inputs(); mouse=Mouse()
session=ManualDiscardSession(mouse,profile,0,"0p",Path(sys.argv[1]))
print(json.dumps(session.start(report,fresh=True,now=time.monotonic())),flush=True)
while session.phase=="review":
 session.tick(report,fresh=True,now=time.monotonic())
 time.sleep(.01)
result=session.tick(report,[("game",confirmed())],fresh=True,now=time.monotonic())
print(json.dumps({**result,"clicks":len(mouse.clicks)}),flush=True)
"""
    ticket = tmp_path / "ipc.json"
    process = subprocess.Popen([sys.executable, "-u", "-c", script, str(ticket)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    try:
        # Selection is tiny; communicate below bounds all remaining child work.
        first = json.loads(process.stdout.readline())
        assert process.poll() is None
        ticket.write_text(json.dumps(first["confirmation"]), encoding="utf-8")
        output, errors = process.communicate(timeout=15)
        assert process.returncode == 0, errors
        result = json.loads(output.strip())
        assert result["confirmed"] and result["clicks"] == 2
    finally:
        if process.poll() is None:
            process.kill(); process.communicate(timeout=5)


def test_observation_token_mismatch_never_sends_selection(tmp_path):
    report, mouse, session = setup(tmp_path)
    with pytest.raises(ValueError, match="Observed board changed"):
        session.start(report, fresh=True, now=10, expected_token="stale-observation")
    assert not mouse.clicks and session.phase == "failed"
