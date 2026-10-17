import json
from pathlib import Path
import pytest

from games.mahjong_soul.live.runtime.session import SessionJournal,RecordingMouse,AgentLease
from agents.mahjong_soul.inspect_run import summarize
from tests.mahjong_soul.test_auto import Mouse


def test_session_links_frames_decisions_inputs_and_confirmations(tmp_path):
    journal=SessionJournal(tmp_path);mouse=Mouse();backend=RecordingMouse(mouse,journal)
    journal.frame(b'png',report={'state_ready':True},geometry={'width':1920},phase='before_input')
    journal.write('decision',event={'action':{'kind':'discard','tile':'1m'}})
    backend.double_click(.5,.9,1920,1080)
    journal.write('confirmed',step=2)
    journal.close()
    rows=[json.loads(l) for l in (journal.directory/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    attempt=next(row for row in rows if row['kind']=='input_attempt')
    assert (journal.directory/attempt['preceding_image']).read_bytes()==b'png'
    assert [r['kind'] for r in rows].index('input_attempt')<[r['kind'] for r in rows].index('input_delivered')
    report=summarize(journal.directory)
    assert report['counts']['confirmed']==1 and len(mouse.clicks)==1
    assert json.loads((journal.directory/'summary.json').read_text())['status']=='stopped'


def test_recording_failure_prevents_input(tmp_path):
    journal=SessionJournal(tmp_path);mouse=Mouse();backend=RecordingMouse(mouse,journal)
    journal.max_bytes=journal.used
    with pytest.raises(OSError):backend.click(.5,.9,1920,1080)
    assert not mouse.clicks
    with pytest.raises(OSError):journal.close('recording_limit')
    assert json.loads((journal.directory/'summary.json').read_text())['status']=='recording_limit'


def test_partial_input_is_recorded_without_retry(tmp_path):
    journal=SessionJournal(tmp_path)
    class Broken:
        def click(self,*args):raise OSError('Partial delivery')
    with pytest.raises(OSError):RecordingMouse(Broken(),journal).click(.5,.9,1920,1080)
    journal.close('blocked');report=summarize(journal.directory)
    assert report['counts']['input_attempt']==1
    assert report['recent_issues'][-1]['reason']=='Partial delivery'


def test_os_lock_prevents_two_agents_and_releases_on_close(tmp_path):
    first=AgentLease(tmp_path/'agent.lock')
    with pytest.raises(ValueError,match='already running'):AgentLease(tmp_path/'agent.lock')
    first.close()
    second=AgentLease(tmp_path/'agent.lock');second.close()



def test_restart_preserves_attempted_game_step_without_rebuilding_pending(tmp_path):
    from games.mahjong_soul.live.runtime.session import prior_attempts
    from games.mahjong_soul.live.runtime.controller import InputController
    from games.mahjong_soul.live.runtime.input import plan_discard
    from tests.mahjong_soul.test_input import inputs
    report,profile=inputs();key=InputController._key(report,report['state']['step'])
    journal=SessionJournal(tmp_path);journal.write('plan',attempt_key=key)
    backend=RecordingMouse(Mouse(),journal);backend.click(.5,.9,1920,1080);journal.close('interrupted')
    recovered=prior_attempts(tmp_path)
    assert recovered=={key}
    controller=InputController(Mouse(),attempted_keys=recovered)
    assert controller.snapshot()['pending'] is None
    with pytest.raises(ValueError,match='already attempted'):
        controller.submit(plan_discard(report,profile,0,'0p',now=1),report,enabled=True,now=1)
