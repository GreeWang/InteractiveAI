"""Build saved Unity fixtures and preflight real exported states, without model calls."""
import copy
import json
import math
from pathlib import Path
from common import ROOT,read,write,digest,timestamp
from engine import Engine
from online_check import check,compare
from offline_score import score
from provider import Lock

def canonical(s):
    def rounder(v):
        if isinstance(v,float):return round(v,6)
        if isinstance(v,list):return [rounder(x) for x in v]
        if isinstance(v,dict):return {k:rounder(x) for k,x in v.items() if k!='state_version'}
        return v
    return digest(rounder(s))

def negative_cases(t,reference):
    c=t['contract'];objs={o['id']:o for o in reference['objects']};first=next(iter(c['allowed']));out=[]
    if c['relative']:
        x=c['relative'][0][1];p=objs[x]['position'][:];p[0]+=.03
        out.append(('relative_layout_changed',[dict(op='set',id=x,position=p)]))
    if c['inside']:
        x,rid=c['inside'][0];r=next(r for r in c['regions'] if r['id']==rid);p=objs[x]['position'][:];p[0]=r['max'][0]
        out.append(('center_inside_body_outside',[dict(op='set',id=x,position=p)]))
    if c['support']:
        x=c['support'][0][0];p=objs[x]['position'][:];p[1]+=.06
        out.append(('floating_above_support',[dict(op='set',id=x,position=p)]))
    if c['facing']:
        x=c['facing'][0][0];yaw=objs[x]['rotation'][1]+35
        if t['id']=='M04':
            old=next(o for o in t['initial']['objects'] if o['id']=='T')['position'];p=objs[x]['position'];yaw=math.degrees(math.atan2(old[0]-p[0],old[2]-p[2]))
        out.append(('old_table_facing' if t['id']=='M04' else 'incorrect_heading',[dict(op='set',id=x,rotation=[0,yaw,0])]))
    locked=next(x for x in objs if x not in c['allowed'] and x!='Floor');p=objs[locked]['position'][:];p[0]+=.03
    out.append(('protected_object_moved',[dict(op='set',id=locked,position=p)]))
    if t['id'] in ['M05','M06']:
        p=objs['C3']['position'][:];p[0]+=.03
        out.append(('yaw_only_chair_position_changed',[dict(op='set',id='C3',position=p)]))
    if len(c['allowed'])>1:
        a,b=list(c['allowed'])[:2]
        out.append(('target_overlap',[dict(op='set',id=b,position=objs[a]['position'])]))
    return out

def run(render=True):
    engine=Engine();context=engine.context()
    if context['dirty'] or context['count']!=1:raise RuntimeError('User scene must be one clean scene before reset; current scene was not modified')
    write(ROOT/'preflight/original_context.json',context)
    manifest=read(ROOT/'task_manifest.json');records=[];failures=[]
    try:
        for tid in manifest['formal']+manifest['development']:
            task=read(ROOT/'tasks'/(tid+'.json'));folder=ROOT/'preflight'/tid;folder.mkdir(exist_ok=True)
            initial=engine.reset(task,tid+'_initial');engine.decorate(task['contract']);initial=engine.save(tid+'_initial');write(folder/'initial_state.json',initial)
            write(folder/'public_contract.json',task['contract'])
            init_grade=score(initial,initial,task['contract']);assert not init_grade['success'],(tid,'initial already complete')
            write(folder/'initial_score.json',init_grade)
            if render and tid in manifest['formal']:engine.render(folder/'initial.png')
            edits=[dict(id=i,position=o['position'],yaw=o['yaw']) for i,o in task['witness'].items()]
            engine.apply(edits);reference=engine.inspect();online=check(reference,initial,task['contract']);diff=compare(reference,initial,task['contract']);grade=score(reference,initial,task['contract'])
            write(folder/'reference_state.json',reference);write(folder/'reference_online.json',online);write(folder/'reference_diff.json',diff);write(folder/'reference_score.json',grade)
            assert online['passed'] and diff['passed'] and grade['success'],(tid,[r for r in grade['checks'] if not r['passed']])
            # Check exported Renderer bounds against independently calculated proxy geometry.
            bounds_errors=[]
            design=read(ROOT.parent/'check_protocol_v2/work/task_design.json') if tid in manifest['formal'] else None
            if design:
                d=next(x for x in design['tasks'] if x['id']==tid);expected={**d['initial'],**d['witness']}
                for o in reference['objects']:
                    if o['id']=='Floor':continue
                    v=expected[o['id']];yaw=math.radians(v['yaw']);size=v['size'];ext=[(abs(math.cos(yaw))*size[0]+abs(math.sin(yaw))*size[2])/2,size[1]/2,(abs(math.sin(yaw))*size[0]+abs(math.cos(yaw))*size[2])/2]
                    err=max(abs(o[key][j]-(v['position'][j]+sgn*ext[j])) for key,sgn in [('bounds_min',-1),('bounds_max',1)] for j in range(3))
                    if err>1e-4:bounds_errors.append(dict(id=o['id'],max_error=err))
            assert not bounds_errors,(tid,bounds_errors)
            reloaded=engine.save(tid+'_reference');assert canonical(reloaded)==canonical(reference),(tid,'save/reopen drift')
            if render:
                engine.render(folder/'reference.png')
                if tid in manifest['formal']:engine.render(folder/'reference_top.png',True)
            # Each negative uses a fresh valid reference, never another negative's state.
            negatives=[]
            for name,mutation in negative_cases(task,reference):
                engine.evaluate('UnityEditor.SceneManagement.EditorSceneManager.OpenScene('+json.dumps('Assets/P2SCV1/Scenes/check_v2_'+tid+'_reference.unity')+');return true;')
                engine.call(dict(op='apply',edits=mutation));bad=engine.inspect()
                report=check(bad,initial,task['contract']);audit=compare(bad,initial,task['contract']);independent=score(bad,initial,task['contract'])
                detected=not(report['passed'] and audit['passed']);assert detected and not independent['success'],(tid,name)
                write(folder/(name+'.json'),dict(mutation=mutation,state=bad,online=report,diff=audit,offline=independent,not_agent_result=True))
                negatives.append(dict(case=name,online_detected=detected,offline_detected=not independent['success']))
            reset=engine.reset(task,tid+'_reset_verification');engine.decorate(task['contract']);reset=engine.save(tid+'_reset_verification')
            assert canonical(reset)==canonical(initial),(tid,'reset mismatch')
            # Ensure invalid basic calls are rejected before writing to the scene.
            before=canonical(reset)
            for edit in [dict(id='INVALID_OBJECT',yaw=0),dict(id=next(iter(task['contract']['allowed'])),position=[float('nan'),0,0])]:
                try:engine.apply([edit]);raise AssertionError('invalid write was accepted')
                except ValueError:pass
            assert canonical(engine.inspect())==before
            rec=dict(id=tid,passed=True,initial_incomplete=True,reference_online_passed=True,reference_offline_passed=True,save_reopen_stable=True,reset_stable=True,bounds_crosscheck=True,negative_cases=negatives,initial_scene='Assets/P2SCV1/Scenes/check_v2_'+tid+'_initial.unity',reference_scene='Assets/P2SCV1/Scenes/check_v2_'+tid+'_reference.unity',initial_hash=canonical(initial),contract_hash=digest(task['contract']))
            records.append(rec);write(ROOT/'preflight/progress.json',dict(time=timestamp(),completed=records));print('PREFLIGHT',tid,'PASS',len(negatives),'negative cases',flush=True)
    except Exception as e:
        failures.append(dict(error=type(e).__name__,detail=str(e)));raise
    finally:
        engine.restore(context)
        write(ROOT/'preflight/summary.json',dict(time=timestamp(),passed=len(records)==16 and not failures,formal_count=len([r for r in records if r['id'] in manifest['formal']]),development_fixture_count=len([r for r in records if r['id'] in manifest['development']]),records=records,failures=failures,original_context_restored=engine.context()==context,model_calls=0))

if __name__=='__main__':
    with Lock(ROOT/'unity_execution.lock'):run()
