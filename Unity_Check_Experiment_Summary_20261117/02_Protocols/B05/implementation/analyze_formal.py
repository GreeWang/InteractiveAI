"""Independent post-run checks and descriptive pilot report; never feeds the actor."""
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from common import ROOT, read, write, timestamp
from engine import Engine
from online_check import check, compare
from offline_score import score
from feedback import check_feedback
from preflight_v3 import canonical
from provider import Ledger, ledger_entries
from run_development import compact, initial_messages
from run_formal import verify_freeze


def hashes_match(base, values):
    bad=[n for n,v in values.items() if not (base/n).is_file() or hashlib.sha256((base/n).read_bytes()).hexdigest()!=v]
    return dict(checked=len(values),passed=not bad,failures=bad)


def ordered(trace):
    edits=[i for i,e in enumerate(trace) if e.get('tool')=='apply_edits' and 'error' not in e.get('observation',{})]
    for n,i in enumerate(edits):
        v=trace[i]['observation']['state_version'];end=edits[n+1] if n+1<len(edits) else len(trace)
        tools=[e['tool'] for e in trace[i+1:end] if e.get('tool') in ['check_constraints','compare_state'] and e.get('observation',{}).get('state_version')==v]
        if tools[:2]!=['check_constraints','compare_state']:return False
    return bool(edits)


def main():
    verify_freeze();s=read(ROOT/'formal/summary.json');schedule=read(ROOT/'formal/schedule.json')['cells'];assert s['completed']==len(schedule)==48
    cfg=read(ROOT/'config.json');ledger=Ledger(ROOT/'cost_ledger.ndjson',cfg);entries={e['request_id']:e for e in ledger_entries(ledger.path)}
    audit=dict(time=timestamp(),frozen_sources_match=True,cells=[],old_evidence={})
    for base,m in read(ROOT/'audit/previous_evidence_manifest.json').items():audit['old_evidence'][base]=hashes_match(Path(base),m)
    old=ROOT.parent/'check_v2_formal';u=read(old/'analysis/unity_evidence_manifest.json')
    audit['old_unity_assets']=hashes_match(Path('/'),{**u['asset_sha256'],**u['meta_sha256']})
    audit['unity_implementation']=hashes_match(Path('/'),read(old/'formal/frozen_configuration.json')['project_sha256'])
    uv=read(ROOT.parent/'check_v3_development/audit/unity_evidence_manifest.json')
    audit['v3_pilot_unity_assets']=hashes_match(Path('/'),{**uv['asset_sha256'],**uv['meta_sha256']})
    audit['context_restored']=s['original_context_restored'] and Engine().context()==read(ROOT/'formal/started.json')['original_context']
    rows=[];failures={phase:{g:Counter() for g in ['G2','G4']} for phase in ['first_edit','final']};wire_full=wire_lean=0;repairs=[]
    for cell in schedule:
        folder=ROOT/'formal'/cell['run_id'];r=read(folder/'result.json');assert r==next(v for v in s['results'] if v['run_id']==r['run_id'])
        initial,final=read(folder/'initial_state.json'),read(folder/'final_state.json');task=read(ROOT/'tasks'/(r['task_id']+'.json'));c=task['contract']
        trace=[json.loads(x) for x in (folder/'trace.ndjson').read_text().splitlines()] if (folder/'trace.ndjson').exists() else []
        edits=[read(p) for p in sorted(folder.glob('after_edit_*.json'))];states={v['state_version']:v for v in [initial]+edits}
        grade=score(final,initial,c);grades=[score(v,initial,c) for v in edits];diag_ok=True
        for e in trace:
            tool=e.get('tool');obs=e.get('observation',{})
            if tool not in ['check_constraints','compare_state'] or 'error' in obs:continue
            v=obs['state_version'];full=(check if tool=='check_constraints' else compare)(states[v],initial,c)
            saved=read(folder/f'diagnostic_full_{e["turn"]:02}.json')
            diag_ok &= saved==dict(tool=tool,state_version=v,contract_version=c['contract_version'],result=full)
            expected=check_feedback(full) if tool=='check_constraints' else copy_dict(full)
            expected.update(state_version=v,contract_version=c['contract_version']);diag_ok &= compact(expected)==obs
            if tool=='check_constraints':
                full=dict(full,state_version=v,contract_version=c['contract_version'])
                wire_full+=len(json.dumps(compact(full),ensure_ascii=False,separators=(',',':')).encode())
                wire_lean+=len(json.dumps(obs,ensure_ascii=False,separators=(',',':')).encode())
        requests=[read(p) for p in sorted(folder.glob('request_*.json'))];responses=[read(p) for p in sorted(folder.glob('response_*.json'))]
        local=[e for e in entries.values() if e['key'].startswith(r['run_id']+'_request_')];known=[e for e in local if e['status']=='completed'];unknown=[e for e in local if e['status']=='reserved_unknown']
        stats=r['stats'];tokens_ok=(sum(p['usage']['prompt_tokens'] for p in responses)==stats['input_tokens'] and sum(p['usage']['completion_tokens'] for p in responses)==stats['output_tokens'])
        request_ok=len(local)==len(requests)==stats['requests']==len(responses)+len(unknown) and len(trace)==len(responses)
        resource_ok=True;used_input=used_output=0;phase=False
        for j,p in enumerate(requests):
            b=json.loads(p['messages'][-1]['content'])['resource_budget'];resource_ok &= b['remaining_input_tokens']==96000-used_input and b['remaining_output_tokens']==12000-used_output and b['remaining_seconds']>=0 and (not phase or b['finish_only'])
            resource_ok &= p['seed']==cell['seed'] and p['model']==cfg['model'] and p['temperature']==cfg['temperature'] and p['enable_thinking'] is False
            phase=b['finish_only']
            ev=next(e for e in local if e['key']==r['run_id']+'_request_'+str(j+1))
            resource_ok &= ev['input_bound']==p['input_bound'] and ev['output_bound']==(750 if phase else min(2048,12000-used_output))
            if j<len(responses):
                usage=responses[j]['usage'];resource_ok &= usage['prompt_tokens']<=p['input_bound'] and usage['completion_tokens']<=ev['output_bound']
                used_input+=usage['prompt_tokens'];used_output+=usage['completion_tokens']
        flags_ok=(r['state_success']==grade['success'] and r['complete_success']==(r['normal_finish'] and grade['success'])
            and r['initial_edit_failed']==(bool(grades) and not grades[0]['success'])
            and r['self_repaired']==(bool(grades) and not grades[0]['success'] and grade['success'])
            and r['false_complete']==bool(r['finish'] and r['finish']['status']=='complete' and not grade['success'])
            and r['process_protection_violation']==any(g['protection_violation'] for g in grades)
            and r['final_protection_violation']==grade['protection_violation'])
        actor_report=(r['finish'] is None or any(e.get('tool')=='finish' and e.get('arguments')==r['finish'] and e.get('observation',{}).get('submitted') for e in trace))
        adherence=(all(any(e.get('tool')==t and e.get('observation',{}).get('state_version')==v['state_version'] for e in trace) for v in edits for t in ['check_constraints','compare_state']) if r['group']=='G4' else None)
        item=dict(run_id=r['run_id'],metadata_matches=all(r[k]==cell[k] for k in ['run_id','task_id','group','repeat','seed','block']),initial_matches_preflight=canonical(initial)==canonical(read(ROOT/'preflight'/r['task_id']/'initial_state.json')),
            prompts_match=read(folder/'initial_context.json')['messages']==initial_messages(task,r['group'],initial,cfg)[0],
            independent_scores_match=grade==read(folder/'offline_final_score.json') and all(g==read(folder/f'offline_edit_{i+1:02}.json') for i,g in enumerate(grades)),
            flags_match=flags_ok,diagnostics_match=diag_ok,request_usage_match=request_ok and tokens_ok,resource_and_bounds_match=bool(resource_ok),
            known_cost_matches=math.isclose(sum(e['charged_upper_cny'] for e in known),stats['cost_cny'],abs_tol=1e-12),
            actor_wrote_finish=bool(actor_report),flow_metric_matches=adherence==r['flow_adherence'],
            online_offline_agree=check(final,initial,c)['passed']==grade['success'],
            caps_passed=all(stats[k]<=cfg['limits'][k] for k in cfg['limits'] if k!='seconds') and r['seconds']<=1200,
            images_present=all((folder/n).exists() for n in ['final.png','final_top.png']),
            length_limited_responses=sum(p['choices'][0].get('finish_reason')=='length' for p in responses),
            json_parse_errors=sum(e.get('observation',{}).get('error')=='JSONDecodeError' for e in trace),
            finish_schema_errors=sum(e.get('tool')=='finish' and e.get('observation',{}).get('error')=='ValueError' for e in trace),
            tool_errors=sum('error' in e.get('observation',{}) for e in trace))
        audit['cells'].append(item)
        initial_grade=grades[0] if grades else score(initial,initial,c)
        for phase_name,g in [('first_edit',initial_grade),('final',grade)]:failures[phase_name][r['group']].update({x['rule_id'].split(':')[0] for x in g['checks'] if not x['passed']})
        rows.append(dict(run_id=r['run_id'],task_id=r['task_id'],group=r['group'],repeat=cell['repeat'],seed=cell['seed'],block=cell['block'],normal_finish=r['normal_finish'],complete_success=r['complete_success'],state_success=r['state_success'],finish_status=r['finish']['status'] if r['finish'] else 'no_report',
            initial_edit_failed=r['initial_edit_failed'],self_repaired=r['self_repaired'],false_complete=r['false_complete'],flow_adherence=r['flow_adherence'],ordered_flow=ordered(trace) if r['group']=='G4' else None,
            report_phase_entered=bool(r['finalization']),stop_reason=r['stop_reason'],seconds=r['seconds'],wall_seconds=r['wall_seconds'],**stats,
            failed_final_rules=';'.join(x['rule_id'] for x in grade['checks'] if not x['passed'])))
        if r['self_repaired']:repairs.append(dict(run_id=r['run_id'],first_failed=[x['rule_id'] for x in grades[0]['checks'] if not x['passed']],final_success=True))
    exceptions=read(ROOT/'audit/unknown_request_exceptions.json')['exceptions'] if (ROOT/'audit/unknown_request_exceptions.json').exists() else []
    audit['ledger_accounted']=all(e['status']=='completed' or any(x['request_id']==e['request_id'] and x['scope']=='formal' and x['preserve_full_reservation'] and math.isclose(x['reserved_cny'],e['charged_upper_cny'],abs_tol=1e-12) for x in exceptions) for e in entries.values())
    audit['no_logical_retries']=len({e['key'] for e in entries.values()})==len(entries)
    audit['local_cost_matches']=math.isclose(sum(e['charged_upper_cny'] for e in entries.values()),s['ledger_totals']['total'],abs_tol=1e-12)
    audit['global_totals']=ledger.global_totals();audit['within_cost_caps']=s['ledger_totals']['total']<=15 and audit['global_totals']['total']<=300
    bool_keys=[k for k,v in audit['cells'][0].items() if isinstance(v,bool)]
    audit['passed']=all(all(c[k] for k in bool_keys) for c in audit['cells']) and all(v['passed'] for v in audit['old_evidence'].values()) and all(audit[k]['passed'] for k in ['old_unity_assets','v3_pilot_unity_assets','unity_implementation']) and all(audit[k] for k in ['context_restored','ledger_accounted','no_logical_retries','local_cost_matches','within_cost_caps'])
    write(ROOT/'audit/results.json',audit);assert audit['passed'],'Inspect audit/results.json; do not change recorded outcomes'
    metrics={}
    for group in ['G2','G4']:
        rr=[r for r in s['results'] if r['group']==group];m={k:sum(bool(r[k]) for r in rr) for k in ['complete_success','state_success','normal_finish','initial_edit_failed','self_repaired','false_complete','process_protection_violation','final_protection_violation']}
        m.update(runs=24,no_report=sum(r['finish'] is None for r in rr),report_phase_entered=sum(bool(r['finalization']) for r in rr),
            complete_claims=sum(bool(r['finish'] and r['finish']['status']=='complete') for r in rr),
            technical_failures=sum(bool(r['transport_failure']) for r in rr),
            tool_errors=sum(c['tool_errors'] for c in audit['cells'] if f'_{group}_' in c['run_id']),
            length_limited_responses=sum(c['length_limited_responses'] for c in audit['cells'] if f'_{group}_' in c['run_id']),
            json_parse_errors=sum(c['json_parse_errors'] for c in audit['cells'] if f'_{group}_' in c['run_id']),
            finish_schema_errors=sum(c['finish_schema_errors'] for c in audit['cells'] if f'_{group}_' in c['run_id']),
            ordered_flow=sum(bool(row['ordered_flow']) for row in rows if row['group']==group) if group=='G4' else None,
            flow_gap_with_report_phase=sum(r['flow_adherence'] is False and bool(r['finalization']) for r in rr) if group=='G4' else None,
            flow_gap_without_report_phase=sum(r['flow_adherence'] is False and not r['finalization'] for r in rr) if group=='G4' else None,
            unknown_reserved_cny=sum(e['charged_upper_cny'] for e in entries.values() if e['status']=='reserved_unknown' and f'_{group}_' in e['key']),
            flow_adherence=sum(bool(r['flow_adherence']) for r in rr) if group=='G4' else None,
            stop_reasons=dict(Counter(r['stop_reason'] for r in rr)),mean_seconds=statistics.mean(r['seconds'] for r in rr),
            stats={k:sum(r['stats'][k] for r in rr) for k in rr[0]['stats']})
        metrics[group]=m
    result=dict(time=timestamp(),completed=48,metrics=metrics,runs=rows,repairs=repairs,failure_categories=failures,
        execution_summary=dict(all_actor_reports=all(r['normal_finish'] for r in s['results']),
            no_input_precheck_abandonment=all(r['stop_reason']!='input_budget_precheck' for r in s['results']),
            actual_report_phase_exercised=any(r['finalization'] for r in s['results'])),
        actual_feedback_bytes=dict(full=wire_full,lean=wire_lean,reduction_fraction=1-wire_lean/wire_full),
        local_ledger=s['ledger_totals'],global_local_upper=audit['global_totals'],audit_passed=True,
        interpretation='New instances of six known families; task-level paired analysis. Different-task cross-version rates are descriptive only.')
    add_task_analysis(result,s['results'])
    write(ROOT/'formal/analysis.json',result)
    with (ROOT/'formal/runs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(audit=True,metrics=metrics,feedback=result['actual_feedback_bytes'],global_upper=audit['global_totals']),ensure_ascii=False,indent=2))


def copy_dict(value):return dict(value)


def bootstrap(values,seed,draws=10000):
    import random
    rng=random.Random(seed);means=sorted(sum(rng.choice(values) for _ in values)/len(values) for _ in range(draws))
    def q(frac):
        n=(len(means)-1)*frac;lo=math.floor(n);hi=math.ceil(n)
        return means[lo]+(means[hi]-means[lo])*(n-lo)
    return [q(.025),q(.975)]


def add_task_analysis(result,results):
    plan=read(ROOT/'formal/analysis_plan.json');tasks=[]
    for tid in plan['formal_task_ids']:
        row=dict(task_id=tid)
        for group in ['G2','G4']:
            rr=[r for r in results if r['task_id']==tid and r['group']==group]
            row[group]=dict(success=sum(r['complete_success'] for r in rr),state_success=sum(r['state_success'] for r in rr),
                normal_finish=sum(r['normal_finish'] for r in rr),repairs=sum(r['self_repaired'] for r in rr),
                false_complete=sum(r['false_complete'] for r in rr),no_report=sum(r['finish'] is None for r in rr))
        row['success_difference']=(row['G4']['success']-row['G2']['success'])/2;tasks.append(row)
    families=[]
    for name,ids in plan['families'].items():
        families.append(dict(family=name,tasks=ids,**{g:sum(t[g]['success'] for t in tasks if t['task_id'] in ids) for g in ['G2','G4']},
            success_difference=statistics.mean(t['success_difference'] for t in tasks if t['task_id'] in ids)))
    diffs=[t['success_difference'] for t in tasks]
    result.update(tasks=tasks,families=families,primary_effect=dict(task_mean_difference=statistics.mean(diffs),
        task_bootstrap_95=bootstrap(diffs,plan['bootstrap']['seed']),family_bootstrap_95=bootstrap([f['success_difference'] for f in families],plan['bootstrap']['seed']),
        improved_tasks=sum(v>0 for v in diffs),unchanged_tasks=sum(v==0 for v in diffs),worse_tasks=sum(v<0 for v in diffs)))
    pairs=Counter()
    for tid in plan['formal_task_ids']:
        for repeat in [1,2]:
            p={r['group']:r['complete_success'] for r in results if r['task_id']==tid and r['repeat']==repeat}
            pairs['both_success' if all(p.values()) else 'both_failure' if not any(p.values()) else 'G4_only_success' if p['G4'] else 'G2_only_success']+=1
    result['paired_run_outcomes']=pairs
    affected={r['block'] for r in results if r['transport_failure']}
    result['technical_failure_cells']=[r['run_id'] for r in results if r['transport_failure']]
    result['infrastructure_sensitivity']=dict(excluded_blocks=sorted(affected),**{g:dict(success=sum(r['complete_success'] for r in results if r['group']==g and r['block'] not in affected),
        denominator=sum(r['group']==g and r['block'] not in affected for r in results),
        mean_seconds=statistics.mean(r['seconds'] for r in results if r['group']==g and r['block'] not in affected)) for g in ['G2','G4']})
    local=ledger_entries(ROOT/'cost_ledger.ndjson');result['billing']=dict(requests=len(local),completed=sum(e['status']=='completed' for e in local),
        unknown=sum(e['status']=='reserved_unknown' for e in local),known_cny=sum(e['charged_upper_cny'] for e in local if e['status']=='completed'),
        unknown_reserved_cny=sum(e['charged_upper_cny'] for e in local if e['status']=='reserved_unknown'))
    cfg=read(ROOT/'config.json');aggregate={}
    for path in cfg['global_budget']['ledger_sources']+[str(ROOT/'cost_ledger.ndjson')]:
        for e in ledger_entries(path):
            if e['request_id'] not in aggregate or e['charged_upper_cny']>aggregate[e['request_id']]['charged_upper_cny']:aggregate[e['request_id']]=e
    write(ROOT/'audit/aggregate_ledger_snapshot.json',dict(time=timestamp(),basis='Conservative local request-ID deduplication; not provider billing statement',
        total_upper_cny=sum(e['charged_upper_cny'] for e in aggregate.values()),entries=list(aggregate.values())))


if __name__=='__main__':main()

