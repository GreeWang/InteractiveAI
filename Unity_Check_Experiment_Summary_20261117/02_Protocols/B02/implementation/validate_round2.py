"""Recheck prior real snapshots and exercise signed feedback inside Unity, no model."""
import importlib.util,json,math
from pathlib import Path
from common import ROOT,read,write,timestamp
from online_check import check,compare
from offline_score import score
from engine import Engine
from prepare import canonical
from provider import Lock

OLD=ROOT.parent/'check_v2_execution'

def run():
    spec=importlib.util.spec_from_file_location('round1_online',OLD/'online_check.py');previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    cases=[]
    manifest=read(ROOT/'task_manifest.json')
    for tid in manifest['formal']+manifest['development']:
        task=read(ROOT/'tasks'/(tid+'.json'));folder=OLD/'preflight'/tid;initial=read(folder/'initial_state.json')
        states=[('initial',initial),('reference',read(folder/'reference_state.json'))]
        for p in folder.glob('*.json'):
            d=read(p)
            if isinstance(d,dict) and 'mutation' in d:states.append((p.stem,d['state']))
        for name,s in states:
            old=previous.check(s,initial,task['contract']);new=check(s,initial,task['contract'])
            assert [(x['rule_id'],x['passed']) for x in old['rules']]==[(x['rule_id'],x['passed']) for x in new['rules']],(tid,name)
            cases.append(dict(task=tid,case=name,truth_unchanged=True))
    print('REGRESSION',len(cases),'real snapshots: identical rule truth values',flush=True)
    engine=Engine();context=engine.context();assert not context['dirty'] and context['count']==1
    unity=[]
    try:
        for tid in ['D03','D04']:
            task=read(ROOT/'tasks'/(tid+'.json'));folder=ROOT/'preflight/round2_heading'/tid
            original=read(OLD/'development'/(tid+'_G4_r1')/'initial_state.json');failed=read(OLD/'development'/(tid+'_G4_r1')/'final_state.json')
            before=engine.reset({'initial':failed},tid+'_round1_failed_replay');engine.decorate(task['contract']);before=engine.save(tid+'_round1_failed_replay')
            assert canonical(before)==canonical(failed)
            report=check(before,original,task['contract']);edits=[]
            for rule in report['rules']:
                if rule['rule_id'].startswith('facing:'):
                    m=rule['measured'];assert m['direction_defined']
                    edits.append(dict(id=rule['rule_id'].split(':')[1],yaw=(m['current_yaw_deg']+m['signed_error_deg'])%360))
            engine.apply(edits);after=engine.save(tid+'_signed_feedback_validation');independent=score(after,original,task['contract'])
            assert independent['success'],(tid,[x for x in independent['checks'] if not x['passed']])
            assert check(after,original,task['contract'])['passed'] and compare(after,original,task['contract'])['passed']
            write(folder/'diagnostic_validation.json',dict(before=before,feedback=report,researcher_applied_corrections=edits,after=after,independent_score=independent,model_calls=0,not_agent_result=True))
            unity.append(dict(task=tid,feedback_correction_valid=True,independent_success=True))
            print('UNITY SIGNED FEEDBACK',tid,'PASS (researcher preflight, not model repair)',flush=True)
    finally:engine.restore(context)
    write(ROOT/'preflight/round2_feedback_validation.json',dict(time=timestamp(),passed=len(unity)==2,regression_snapshots=len(cases),regression=cases,unity=unity,original_context_restored=engine.context()==context,model_calls=0,source_preflight=str(OLD/'preflight/summary.json')))

if __name__=='__main__':
    with Lock(ROOT/'unity_execution.lock'):run()
