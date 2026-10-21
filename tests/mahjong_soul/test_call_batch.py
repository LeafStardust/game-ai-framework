"""Coverage and fail-closed checks for the exhaustive opening-call batch."""
import json
from pathlib import Path
import pytest
from agents.mahjong_soul import call_batch as batch


def start(wind='E',dealer=0):return {'type':'start_kyoku','bakaze':wind,'oya':dealer}
def pon(tile,actor=2):return {'type':'pon','actor':actor,'pai':tile,'consumed':[tile,tile]}


def test_only_nonvalue_first_openings_and_correct_seat_wind_are_selected():
    events=[start(),pon('S'),pon('3p'),start(dealer=1),pon('S'),pon('9p'),
            start('S'),pon('S'),start(),{'type':'ankan','actor':2},pon('9m')]
    targets=batch.openings(events,2)
    assert [(t['hand_index'],t['called_tile']) for t in targets]==[(0,'2z'),(3,'9m')]


def test_red_call_and_red_consumption_remain_distinct():
    events=[start(),{'type':'pon','actor':2,'pai':'5pr','consumed':['5p','5p']}]
    assert batch.openings(events,2)[0]['called_tile']=='0p'
    assert batch.openings(events,2)[0]['combination']==['5p','5p']
    assert batch.label('5p')=='5p' and batch.label('5pr')=='0p'


def corpus(tmp_path):
    root=tmp_path/'corpus';events=[start(),pon('S'),{'type':'end_kyoku'},start(),pon('S'),{'type':'end_kyoku'}]
    row={'seed':80,'seat':2,'candidate':'east_speed','ranks':[1,2,3]}
    for split,records in [('development',[row]),('held-out',[])]:
        folder=root/f'ready-push-callers-{split}';folder.mkdir(parents=True)
        (folder/'summary.json').write_text(json.dumps({'opponents':'callers','records':records}))
        if records:(folder/'80-2-east_speed.json').write_text(json.dumps({'metrics':row,'events':events}))
    return root,row,events


def fake_runtime(monkeypatch,events,*,bad_baseline=False,bad_divergence=False):
    baseline={'log':[] if bad_baseline else events,'scores':[35000]*3};calls=[]
    targets=[{'opening':True,'value_call':False,'hand_index':i,'action':{'kind':'pon','called_tile':'2z','combination':'2z|2z'},
              'request':{'board_token':str(i)},'analysis':{}} for i in range(2)]
    def capture(*args,**kwargs):calls.append('baseline');return baseline,targets
    def skip(seed,seat,base,target,**kwargs):
        calls.append('skip');index=1+3*target['hand_index']
        branch={'target_hand':{'wins':0},'metrics':{}}
        return {'first_different_event_index':99 if bad_divergence else index,'branches':{'pon':branch,'skip':branch}},events,events
    monkeypatch.setattr(batch,'capture_calls',capture);monkeypatch.setattr(batch,'skip_target',skip)
    return calls


def test_all_targets_reuse_one_baseline_and_finish_complete(tmp_path,monkeypatch):
    root,row,events=corpus(tmp_path);calls=fake_runtime(monkeypatch,events)
    result=batch.run_batch(root,tmp_path/'output',['callers'])
    assert result['complete'] and result['scope']['eligible_calls']==2
    assert len(result['records'])==2 and calls==['baseline','skip','skip']


@pytest.mark.parametrize('fault,match',[('baseline','Baseline replay changed'),('divergence','earlier action')])
def test_changed_replay_or_wrong_intervention_cannot_be_reported_complete(tmp_path,monkeypatch,fault,match):
    root,row,events=corpus(tmp_path)
    fake_runtime(monkeypatch,events,bad_baseline=fault=='baseline',bad_divergence=fault=='divergence')
    with pytest.raises(ValueError,match=match):batch.run_batch(root,tmp_path/'output',['callers'])
    assert not (tmp_path/'output/summary.json').exists()


def test_corpus_duplicate_match_and_existing_output_are_rejected(tmp_path):
    root,row,events=corpus(tmp_path);p=root/'ready-push-callers-development/summary.json'
    p.write_text(json.dumps({'opponents':'callers','records':[row,row]}))
    with pytest.raises(ValueError,match='Duplicate corpus match'):batch.manifest(root,['callers'])
    output=tmp_path/'output';output.mkdir()
    with pytest.raises(ValueError,match='Output already exists'):batch.run_batch(root,output,['callers'])
