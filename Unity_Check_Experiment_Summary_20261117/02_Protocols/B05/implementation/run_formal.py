"""New held-out task formal batch; uses the byte-identical V3 actor loop."""
import hashlib
import random
from common import ROOT,read,write,append,timestamp
from engine import Engine
from preflight_v3 import canonical
from provider import Client,Ledger,Lock,ledger_entries
from run_development import run_cell

AUTH='那就按照你的方法继续；API总预算沿用已授权300元上限。'


def make_schedule(ids,seed):
    rng=random.Random(seed);blocks=[(tid,repeat) for tid in ids for repeat in [1,2]];rng.shuffle(blocks)
    orders=[['G2','G4']]*12+[['G4','G2']]*12;rng.shuffle(orders)
    return [dict(block=i+1,task_id=tid,repeat=repeat,seed=repeat,group=g,run_id=f'{tid}_{g}_r{repeat}') for i,((tid,repeat),order) in enumerate(zip(blocks,orders)) for g in order]


def verify_freeze():
    from pathlib import Path
    frozen=read(ROOT/'formal/frozen_configuration.json')
    for name,v in frozen['sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==v,('Frozen source changed',name)
    for name,v in frozen['project_sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==v,('Unity implementation changed',name)


def continue_after_unknown(ledger,run_id):
    unknown=[e for e in ledger_entries(ledger.path) if e['status']=='reserved_unknown' and e['key'].startswith(run_id+'_request_')]
    if not unknown:return False
    p=ROOT/'audit/unknown_request_exceptions.json';data=read(p) if p.exists() else dict(exceptions=[])
    for e in unknown:data['exceptions'].append(dict(request_id=e['request_id'],scope='formal',reserved_cny=e['charged_upper_cny'],preserve_full_reservation=True,
        user_authorization=AUTH,time=timestamp(),restriction='Continue only original unstarted cells under 300 CNY aggregate and 15 CNY batch limits. No retries or replacements.'))
    write(p,data);append(ROOT/'formal/infrastructure_events.ndjson',dict(time=timestamp(),run_id=run_id,request_ids=[e['request_id'] for e in unknown],action='Retain technical failure and full reservation; continue next planned cell'))
    return True


def main():
    verify_freeze();assert read(ROOT/'formal/readiness.json')['passed']
    assert not (ROOT/'formal/started.json').exists(),'Batch already started; retain attempts'
    cfg=read(ROOT/'config.json');cells=read(ROOT/'formal/schedule.json')['cells'];assert len(cells)==48
    engine=Engine();context=engine.context();assert not context['dirty'] and context['count']==1
    ledger=Ledger(ROOT/'cost_ledger.ndjson',cfg);client=Client(cfg,ledger);results=[]
    write(ROOT/'formal/started.json',dict(time=timestamp(),original_context=context,global_cost_before=ledger.global_totals()))
    try:
        for cell in cells:
            verify_freeze();write(ROOT/'formal/active.json',dict(time=timestamp(),cell=cell))
            task=read(ROOT/'tasks'/(cell['task_id']+'.json'));engine.reset(task,cell['run_id']+'_initial');engine.decorate(task['contract']);initial=engine.save(cell['run_id']+'_initial')
            assert canonical(initial)==canonical(read(ROOT/'preflight'/cell['task_id']/'initial_state.json'))
            folder=ROOT/'formal'/cell['run_id'];r=run_cell(task,cell['group'],engine,client,cfg,folder,initial,seed=cell['seed'],stage='formal')
            r.update(block=cell['block'],repeat=cell['repeat'],seed=cell['seed']);write(folder/'result.json',r);results.append(r)
            write(ROOT/'formal/progress.json',dict(completed=results,planned=48,ledger_totals=ledger.totals(),global_totals=ledger.global_totals()))
            print('FORMAL',len(results),'/48',cell['run_id'],'success',r['complete_success'],'stop',r['stop_reason'],'report_phase',bool(r['finalization']),flush=True)
            if r['transport_failure']:
                if r['transport_failure']!='UnknownOutcome' or not continue_after_unknown(ledger,cell['run_id']):break
    finally:
        engine.restore(context);write(ROOT/'formal/summary.json',dict(time=timestamp(),planned=48,completed=len(results),results=results,
            ledger_totals=ledger.totals(),global_totals=ledger.global_totals(),original_context_restored=engine.context()==context,development_runs=0))


if __name__=='__main__':
    with Lock(ROOT/'unity_execution.lock'):main()
