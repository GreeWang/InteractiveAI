"""Exactly eight new development attempts; preserve all failures and actual costs."""
import hashlib
import random
from pathlib import Path
from common import ROOT, read, write, append, timestamp
from engine import Engine
from preflight_v3 import canonical
from provider import Client, Ledger, Lock, ledger_entries
from run_development import run_cell


AUTH='那你做吧，反正我那个apikey有300块的预算上限，总上限不超就行'


def verify_freeze():
    for name, expected in read(ROOT/'development/frozen_configuration.json')['sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,('Frozen file changed',name)


def continue_new_cells_after_unknown(ledger,run_id):
    pending=[e for e in ledger_entries(ledger.path) if e['status']=='reserved_unknown' and e['key'].startswith(run_id+'_request_')]
    if not pending:return False
    path=ROOT/'audit/unknown_request_exceptions.json'
    data=read(path) if path.exists() else dict(exceptions=[])
    for e in pending:
        data['exceptions'].append(dict(request_id=e['request_id'],scope='pilot',reserved_cny=e['charged_upper_cny'],
            preserve_full_reservation=True,user_authorization=AUTH,time=timestamp(),
            restriction='Continue only unstarted cells within aggregate 300 CNY and local 15 CNY caps; do not retry or replace this failed run.'))
    write(path,data)
    append(ROOT/'development/infrastructure_events.ndjson',dict(time=timestamp(),run_id=run_id,
        action='preserve failure and full reservation; continue next original cell',request_ids=[e['request_id'] for e in pending]))
    return True


def main():
    assert read(ROOT/'preflight/summary.json')['passed']
    assert 'Ran 13 tests' in (ROOT/'unit_tests.log').read_text() and (ROOT/'unit_tests.log').read_text().rstrip().endswith('OK')
    assert not (ROOT/'development/schedule.json').exists(),'Do not replace recorded attempts'
    config=read(ROOT/'config.json');blocks=read(ROOT/'task_manifest.json')['development'];rng=random.Random(config['order_seed']);rng.shuffle(blocks)
    schedule=[dict(task_id=tid,group=g,seed=1,run_id=f'{tid}_{g}_r1') for tid,order in zip(blocks,[['G2','G4'],['G4','G2'],['G2','G4'],['G4','G2']]) for g in order]
    write(ROOT/'development/schedule.json',dict(time=timestamp(),cells=schedule,seed=config['order_seed'],scope='8 development cells only'))
    write(ROOT/'development/analysis_plan.json',dict(time=timestamp(),scope='Engineering pilot, four new development tasks, one attempt per condition and task; not comparable as a causal cross-round effect to older tasks',
        main_checks=['normal actor-written finish','no input_budget_precheck abandonment','full rule evaluations and complete failure feedback','no hidden scoring feedback or auto repairs','caps and preservation'],
        outcomes=['complete_success','state_success','initial_edit_failed','self_repaired','false_complete','no_report','flow_adherence','finalization','tokens','cost','time','failure_categories'],
        denominator={'G2':4,'G4':4},all_failures_retained=True,formal_runs=0))
    files=list(ROOT.glob('*.py'))+list((ROOT/'skills').glob('*.md'))+list((ROOT/'tasks').glob('*.json'))+list((ROOT/'preflight').rglob('*.json'))
    files += [ROOT/x for x in ['config.json','task_manifest.json','task_design.json','unit_tests.log','development/schedule.json','development/analysis_plan.json','audit/previous_evidence_manifest.json','audit/prior_cost_snapshot.json']]
    write(ROOT/'development/frozen_configuration.json',dict(time=timestamp(),sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))
    engine=Engine();context=engine.context();assert not context['dirty'] and context['count']==1
    ledger=Ledger(ROOT/'cost_ledger.ndjson',config);client=Client(config,ledger);results=[]
    write(ROOT/'development/started.json',dict(time=timestamp(),original_context=context,global_cost_before=ledger.global_totals()))
    try:
        for cell in schedule:
            verify_freeze();write(ROOT/'development/active.json',dict(time=timestamp(),cell=cell))
            task=read(ROOT/'tasks'/(cell['task_id']+'.json'));engine.reset(task,cell['run_id']+'_initial');engine.decorate(task['contract']);initial=engine.save(cell['run_id']+'_initial')
            assert canonical(initial)==canonical(read(ROOT/'preflight'/cell['task_id']/'initial_state.json'))
            result=run_cell(task,cell['group'],engine,client,config,ROOT/'development'/cell['run_id'],initial)
            results.append(result);write(ROOT/'development/progress.json',dict(completed=results,planned=8,ledger_totals=ledger.totals(),global_totals=ledger.global_totals()))
            print('DEVELOPMENT',len(results),'/8',cell['run_id'],'success',result['complete_success'],'stop',result['stop_reason'],'report_phase',bool(result['finalization']),flush=True)
            if result['transport_failure']:
                if result['transport_failure']!='UnknownOutcome' or not continue_new_cells_after_unknown(ledger,cell['run_id']):break
    finally:
        engine.restore(context)
        write(ROOT/'development/summary.json',dict(time=timestamp(),completed=len(results),planned=8,results=results,
            ledger_totals=ledger.totals(),global_totals=ledger.global_totals(),original_context_restored=engine.context()==context,formal_runs=0))


if __name__=='__main__':
    with Lock(ROOT/'unity_execution.lock'):main()
