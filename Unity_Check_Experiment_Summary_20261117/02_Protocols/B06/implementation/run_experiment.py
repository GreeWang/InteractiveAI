"""Serial preregistered native-MCP pilot/formal execution; never rerun finished cells."""
import argparse,hashlib,json,random,shutil,traceback
from pathlib import Path
from common import ROOT,read,write,timestamp
from provider import Ledger,Lock,ledger_entries
from native_provider import NativeClient
from run_actor import run_cell


def hashes(base,areas=('Assets','Packages','ProjectSettings')):
    return {str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for area in areas for p in sorted((base/area).rglob('*')) if p.is_file() and 'NativeCapture' not in p.parts}


def prepare():
    cfg=read(ROOT/'config.json');project=Path(cfg['project']);manifest=read(ROOT/'task_manifest.json')
    backup=ROOT/'audit/project_backup'
    if not backup.exists():
        for area in ['Assets','Packages','ProjectSettings']:shutil.copytree(project/area,backup/area)
        write(ROOT/'audit/project_baseline.json',hashes(project))
    for stage,ids,repeats in [('pilot',manifest['development'],1),('formal',manifest['formal'],2)]:
        dest=ROOT/stage;dest.mkdir(exist_ok=True);schedule=dest/'schedule.json'
        if schedule.exists():continue
        rng=random.Random(cfg['order_seed']+(0 if stage=='pilot' else 10000));blocks=[(t,r) for t in ids for r in range(1,repeats+1)];rng.shuffle(blocks);cells=[]
        for block,(task,repeat) in enumerate(blocks,1):
            groups=['G2','G4'] if block%2 else ['G4','G2']
            for group in groups:cells.append(dict(run_id=f'{task}_{group}_r{repeat}',task_id=task,group=group,repeat=repeat,seed=repeat,block=block))
        write(schedule,dict(created=timestamp(),stage=stage,cells=cells,order='randomized task/seed blocks; alternating paired arm order'))
    freeze={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.glob('*.py'))}
    freeze.update({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'config.json',ROOT/'task_manifest.json',ROOT/'probe/clone_tools.json',*sorted((ROOT/'tasks').glob('*.json'))]})
    target=ROOT/'audit/frozen_implementation.json'
    if target.exists():assert read(target)['sha256']==freeze,'Frozen implementation changed'
    else:write(target,dict(created=timestamp(),sha256=freeze))
    plan=ROOT/'audit/analysis_plan.json'
    if not plan.exists():write(plan,dict(created=timestamp(),primary='independent final geometry plus protected state AND valid finish within common resources',comparison='G4 minus G2; 24 per arm in formal; paired fixed tasks/seeds',pilot_gate='Operational native tools/finish/score/save completeness, independent of success rate',task_reuse=manifest['scope'],bootstrap=dict(unit='task',iterations=10000,seed=20261116),secondary=['state success','false complete','repair after first failed changed state','diagnostics in required order before next edit','protection violations','requests/tokens/cost'],limits=cfg['limits'],native_tools=160,shared_extra='finish (study-control MCP)',g4_extra=['check_constraints','compare_state'],interpretation='Original native Unity tool catalog preserved. Standard model function-calling adapter, shared study report tool, task rules and finite resource caps apply. Not an unmodified third-party client. No human participant outcomes. Do not pool old CLI-based runs.'))
    return cfg


def restore_and_record(folder,project):
    before=read(ROOT/'audit/project_baseline.json');after=hashes(project)
    changed=[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
    write(folder/'asset_integrity.json',dict(passed=not changed,changed=changed))
    if changed:
        for name in changed:
            dest=project/name;src=ROOT/'audit/project_backup'/name
            if dest.exists():
                saved=folder/'unauthorized_assets'/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved)
            if src.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
            else:dest.unlink(missing_ok=True)
        r=read(folder/'result.json');r.update(state_success=False,complete_success=False,final_protection_violation=True,process_protection_violation=True)
        r['false_complete']=bool(r.get('finish') and r['finish']['status']=='complete');r['asset_integrity_violation']=changed;write(folder/'result.json',r)
    assert hashes(project)==before,'Project baseline restore failed'


def run(stage):
    cfg=prepare();ledger=Ledger(ROOT/'cost_ledger.ndjson',cfg);client=NativeClient(cfg,ledger);dest=ROOT/stage;schedule=read(dest/'schedule.json')['cells']
    if stage=='formal':
        assert read(ROOT/'pilot/gate.json')['passed'],'Development operational gate not passed'
        write(dest/'start_freeze.json',dict(time=timestamp(),implementation=read(ROOT/'audit/frozen_implementation.json'),schedule=read(dest/'schedule.json'),analysis_plan=read(ROOT/'audit/analysis_plan.json')))
    with Lock(ROOT/'experiment.lock'):
        for i,cell in enumerate(schedule,1):
            folder=dest/'runs'/cell['run_id']
            if (folder/'result.json').exists():continue
            if folder.exists():raise RuntimeError('Incomplete existing attempt requires explicit audit; no automatic rerun: '+str(folder))
            assert hashes(Path(cfg['project']))==read(ROOT/'audit/project_baseline.json'),'Project changed before run'
            print(timestamp(),'START',stage,i,len(schedule),cell['run_id'],flush=True)
            try:
                run_cell(cell,read(ROOT/'tasks'/(cell['task_id']+'.json')),cfg,stage,folder,client)
                restore_and_record(folder,Path(cfg['project']))
            except Exception:
                write(folder/'execution_error.json',dict(time=timestamp(),traceback=traceback.format_exc()))
                raise
            r=read(folder/'result.json');print(timestamp(),'END',cell['run_id'],'success',r['complete_success'],'state',r['state_success'],'finish',r['normal_finish'],'req',r['stats']['requests'],'cost',round(r['stats']['cost_cny'],4),'stop',r['stop_reason'],flush=True)
            unknown=[e for e in ledger_entries(ROOT/'cost_ledger.ndjson') if e['status']!='completed']
            if unknown:
                exceptions=read(ROOT/'audit/unknown_request_exceptions.json') if (ROOT/'audit/unknown_request_exceptions.json').exists() else {'exceptions':[]}
                seen={e['request_id'] for e in exceptions['exceptions']}
                for e in unknown:
                    if e['request_id'] not in seen:exceptions['exceptions'].append(dict(request_id=e['request_id'],scope=stage,reserved_cny=e['charged_upper_cny'],preserve_full_reservation=True,user_authorization='User authorized this complete native-MCP comparison within aggregate 300 CNY; retain failed original cell and full unknown reservation, continue only unstarted cells; never retry unknown calls',time=timestamp()))
                write(ROOT/'audit/unknown_request_exceptions.json',exceptions)
        results=[read(dest/'runs'/c['run_id']/'result.json') for c in schedule];write(dest/'results.json',results)
        checks=dict(all_cells_present=len(results)==len(schedule),all_final_states=all((dest/'runs'/c['run_id']/'final_state.json').exists() for c in schedule),all_final_scenes=all((dest/'runs'/c['run_id']/'final_scene.unity').exists() for c in schedule),all_catalogs_original=all(read(dest/'runs'/c['run_id']/'actual_tool_catalog.json')['official']==read(ROOT/'probe/clone_tools.json') for c in schedule),all_normal_finish=all(r['normal_finish'] for r in results),no_api_transport_failures=all(not r['transport_failure'] for r in results))
        write(dest/'gate.json',dict(time=timestamp(),passed=all(checks[k] for k in ['all_cells_present','all_final_states','all_final_scenes','all_catalogs_original']),checks=checks,note='Valid failure or missing finish is a model outcome, not grounds to change the intervention or discard a cell. Native dispatch/grade/capture failures stop progression.'))
        print('FINISHED',stage,'gate',checks,'budget',ledger.totals(),'aggregate',ledger.global_totals(),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','pilot','formal']);a=p.parse_args()
    if a.stage=='prepare':prepare();print('Prepared schedules, baseline backup and implementation/analysis freeze')
    else:run(a.stage)
