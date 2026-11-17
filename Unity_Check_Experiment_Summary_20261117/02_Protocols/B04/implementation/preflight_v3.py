"""Actual Unity geometry, rule/permission negatives, and feedback regression; no API."""
import copy
import hashlib
import json
import math
from common import ROOT, read, write, digest, timestamp
from engine import Engine
from online_check import check, compare
from offline_score import score
from feedback import check_feedback


def canonical(s):
    from run_development import compact
    return digest(compact({k:v for k,v in s.items() if k!='state_version'}))


def verify_feedback(full):
    lean=check_feedback(full)
    assert lean['passed']==full['passed']
    assert lean['checked_rule_count']==len(full['rules'])
    assert lean['passed_rule_count']+lean['failed_rule_count']==lean['checked_rule_count']
    assert lean['failures']==[{k:r[k] for k in ['rule_id','measured','expected']} for r in full['rules'] if not r['passed']]
    return lean


def regression():
    old=ROOT.parent/'check_v2_formal';count=0;full_bytes=lean_bytes=0
    assert (ROOT/'online_check.py').read_bytes()==(old/'online_check.py').read_bytes()
    assert (ROOT/'offline_score.py').read_bytes()==(old/'offline_score.py').read_bytes()
    for cell in read(old/'formal/schedule.json')['cells']:
        folder=old/'formal'/cell['run_id'];initial=read(folder/'initial_state.json');c=read(old/'tasks'/(cell['task_id']+'.json'))['contract']
        for p in [folder/'initial_state.json']+sorted(folder.glob('after_edit_*.json'))+[folder/'final_state.json']:
            full=check(read(p),initial,c);lean=verify_feedback(full);count+=1
            full_bytes+=len(json.dumps(full,ensure_ascii=False,separators=(',',':')).encode())
            lean_bytes+=len(json.dumps(lean,ensure_ascii=False,separators=(',',':')).encode())
    return dict(snapshots=count,all_failed_rule_details_preserved=True,predicate_source_unchanged=True,
                full_utf8_bytes=full_bytes,lean_utf8_bytes=lean_bytes,reduction_fraction=1-lean_bytes/full_bytes)


def run():
    engine=Engine();context=engine.context();assert not context['dirty'] and context['count']==1
    records=[];failure=None
    try:
        for design in read(ROOT/'task_design.json')['tasks']:
            tid=design['id'];task=read(ROOT/'tasks'/(tid+'.json'));c=task['contract'];folder=ROOT/'preflight'/tid;folder.mkdir()
            engine.reset(task,tid+'_initial');engine.decorate(c);initial=engine.save(tid+'_initial');write(folder/'initial_state.json',initial)
            assert not score(initial,initial,c)['success']
            engine.apply([dict(id=k,position=v['position'],yaw=v['yaw']) for k,v in task['witness'].items()])
            reference=engine.inspect();full=check(reference,initial,c);diff=compare(reference,initial,c);grade=score(reference,initial,c)
            write(folder/'reference_online.json',full);write(folder/'reference_diff.json',diff);write(folder/'reference_score.json',grade)
            assert full['passed'] and diff['passed'] and grade['success'],(tid,[r['rule_id'] for r in grade['checks'] if not r['passed']])
            lean=verify_feedback(full);write(folder/'reference_feedback.json',lean);write(folder/'reference_state.json',reference)
            expected={**design['initial'],**design['witness']}
            for o in reference['objects']:
                if o['id']=='Floor':continue
                v=expected[o['id']];a=math.radians(v['yaw']);s=v['size'];ext=[(abs(math.cos(a))*s[0]+abs(math.sin(a))*s[2])/2,s[1]/2,(abs(math.sin(a))*s[0]+abs(math.cos(a))*s[2])/2]
                assert max(abs(o[key][j]-(v['position'][j]+sign*ext[j])) for key,sign in [('bounds_min',-1),('bounds_max',1)] for j in range(3))<1e-4,(tid,o['id'],'bounds mismatch')
            assert canonical(engine.save(tid+'_reference'))==canonical(reference)
            engine.render(folder/'reference.png');engine.render(folder/'reference_top.png',True)
            objs={o['id']:o for o in reference['objects']};first=next(iter(c['allowed']));mutations=[]
            oid,rid=c['inside'][0];region=next(r for r in c['regions'] if r['id']==rid);p=objs[oid]['position'][:];p[0]=region['max'][0]
            mutations.append(('center_inside_body_outside',[dict(op='set',id=oid,position=p)]))
            p=objs[first]['position'][:];p[1]+=.06;mutations.append(('floating_or_ground_gap',[dict(op='set',id=first,position=p)]))
            locked=next(o for o in objs if o not in c['allowed'] and o!='Floor');p=objs[locked]['position'][:];p[0]+=.03
            mutations.append(('protected_object_moved',[dict(op='set',id=locked,position=p)]))
            a,b=list(c['allowed'])[:2];mutations.append(('overlap',[dict(op='set',id=b,position=objs[a]['position'])]))
            if c['facing']:
                x=c['facing'][0][0];mutations.append(('wrong_yaw',[dict(op='set',id=x,rotation=[0,objs[x]['rotation'][1]+35,0])]))
            if c['relative']:
                x=c['relative'][0][-1];p=objs[x]['position'][:];p[2]+=.03;mutations.append(('relative_layout_changed',[dict(op='set',id=x,position=p)]))
            yaw_only=next((oid for oid,fields in c['allowed'].items() if fields==['yaw']),None)
            if yaw_only:
                p=objs[yaw_only]['position'][:];p[0]+=.03;mutations.append(('yaw_only_position_changed',[dict(op='set',id=yaw_only,position=p)]))
            for name,edits in mutations:
                engine.evaluate('UnityEditor.SceneManagement.EditorSceneManager.OpenScene('+json.dumps('Assets/P2SCV1/Scenes/check_v3d_'+tid+'_reference.unity')+');return true;')
                engine.call(dict(op='apply',edits=edits));bad=engine.inspect();full=check(bad,initial,c);diff=compare(bad,initial,c);grade=score(bad,initial,c)
                assert not full['passed'] and not grade['success'],(tid,name)
                lean=verify_feedback(full)
                if 'protected' in name or 'yaw_only' in name:assert not diff['passed'] and any(r['rule_id']=='permissions' for r in lean['failures'])
                write(folder/(name+'.json'),dict(state=bad,online=full,feedback=lean,diff=diff,offline=grade,not_agent_result=True))
            engine.reset(task,tid+'_reset_verification');engine.decorate(c);reset=engine.save(tid+'_reset_verification');assert canonical(reset)==canonical(initial)
            records.append(dict(task_id=tid,passed=True,objects=len(initial['objects']),rules=lean['checked_rule_count'],negatives=len(mutations),reset_stable=True,independent_bounds=True))
            print('PREFLIGHT',tid,'PASS',len(mutations),'negatives',flush=True)
        reg=regression();write(ROOT/'preflight/feedback_regression.json',reg)
    except Exception as e:
        failure=dict(type=type(e).__name__,message=str(e));raise
    finally:
        engine.restore(context)
        write(ROOT/'preflight/summary.json',dict(time=timestamp(),passed=len(records)==4 and failure is None,records=records,
            failure=failure,model_calls=0,original_context_restored=engine.context()==context))


if __name__=='__main__':run()
