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
from run_pilot import verify_freeze


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
    verify_freeze();s=read(ROOT/'development/summary.json');schedule=read(ROOT/'development/schedule.json')['cells'];assert s['completed']==len(schedule)==8
    cfg=read(ROOT/'config.json');ledger=Ledger(ROOT/'cost_ledger.ndjson',cfg);entries={e['request_id']:e for e in ledger_entries(ledger.path)}
    audit=dict(time=timestamp(),frozen_sources_match=True,cells=[],old_evidence={})
    for base,m in read(ROOT/'audit/previous_evidence_manifest.json').items():audit['old_evidence'][base]=hashes_match(Path(base),m)
    old=ROOT.parent/'check_v2_formal';u=read(old/'analysis/unity_evidence_manifest.json')
    audit['old_unity_assets']=hashes_match(Path('/'),{**u['asset_sha256'],**u['meta_sha256']})
    audit['unity_implementation']=hashes_match(Path('/'),read(old/'formal/frozen_configuration.json')['project_sha256'])
    audit['context_restored']=s['original_context_restored'] and Engine().context()==read(ROOT/'development/started.json')['original_context']
    rows=[];failures={phase:{g:Counter() for g in ['G2','G4']} for phase in ['first_edit','final']};wire_full=wire_lean=0;repairs=[]
    for cell in schedule:
        folder=ROOT/'development'/cell['run_id'];r=read(folder/'result.json');assert r==next(v for v in s['results'] if v['run_id']==r['run_id'])
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
            resource_ok &= p['seed']==1 and p['model']==cfg['model'] and p['temperature']==cfg['temperature'] and p['enable_thinking'] is False
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
        item=dict(run_id=r['run_id'],initial_matches_preflight=canonical(initial)==canonical(read(ROOT/'preflight'/r['task_id']/'initial_state.json')),
            prompts_match=read(folder/'initial_context.json')['messages']==initial_messages(task,r['group'],initial,cfg)[0],
            independent_scores_match=grade==read(folder/'offline_final_score.json') and all(g==read(folder/f'offline_edit_{i+1:02}.json') for i,g in enumerate(grades)),
            flags_match=flags_ok,diagnostics_match=diag_ok,request_usage_match=request_ok and tokens_ok,resource_and_bounds_match=bool(resource_ok),
            known_cost_matches=math.isclose(sum(e['charged_upper_cny'] for e in known),stats['cost_cny'],abs_tol=1e-12),
            actor_wrote_finish=bool(actor_report),flow_metric_matches=adherence==r['flow_adherence'],
            online_offline_agree=check(final,initial,c)['passed']==grade['success'],
            caps_passed=all(stats[k]<=cfg['limits'][k] for k in cfg['limits'] if k!='seconds') and r['seconds']<=1200,
            images_present=all((folder/n).exists() for n in ['final.png','final_top.png']),
            tool_errors=sum('error' in e.get('observation',{}) for e in trace))
        audit['cells'].append(item)
        initial_grade=grades[0] if grades else score(initial,initial,c)
        for phase_name,g in [('first_edit',initial_grade),('final',grade)]:failures[phase_name][r['group']].update({x['rule_id'].split(':')[0] for x in g['checks'] if not x['passed']})
        rows.append(dict(run_id=r['run_id'],task_id=r['task_id'],group=r['group'],normal_finish=r['normal_finish'],complete_success=r['complete_success'],state_success=r['state_success'],finish_status=r['finish']['status'] if r['finish'] else 'no_report',
            initial_edit_failed=r['initial_edit_failed'],self_repaired=r['self_repaired'],false_complete=r['false_complete'],flow_adherence=r['flow_adherence'],ordered_flow=ordered(trace) if r['group']=='G4' else None,
            report_phase_entered=bool(r['finalization']),stop_reason=r['stop_reason'],seconds=r['seconds'],wall_seconds=r['wall_seconds'],**stats,
            failed_final_rules=';'.join(x['rule_id'] for x in grade['checks'] if not x['passed'])))
        if r['self_repaired']:repairs.append(dict(run_id=r['run_id'],first_failed=[x['rule_id'] for x in grades[0]['checks'] if not x['passed']],final_success=True))
    exceptions=read(ROOT/'audit/unknown_request_exceptions.json')['exceptions'] if (ROOT/'audit/unknown_request_exceptions.json').exists() else []
    audit['ledger_accounted']=all(e['status']=='completed' or any(x['request_id']==e['request_id'] and x['preserve_full_reservation'] and math.isclose(x['reserved_cny'],e['charged_upper_cny'],abs_tol=1e-12) for x in exceptions) for e in entries.values())
    audit['no_logical_retries']=len({e['key'] for e in entries.values()})==len(entries)
    audit['local_cost_matches']=math.isclose(sum(e['charged_upper_cny'] for e in entries.values()),s['ledger_totals']['total'],abs_tol=1e-12)
    audit['global_totals']=ledger.global_totals();audit['within_cost_caps']=s['ledger_totals']['total']<=15 and audit['global_totals']['total']<=300
    bool_keys=[k for k,v in audit['cells'][0].items() if isinstance(v,bool)]
    audit['passed']=all(all(c[k] for k in bool_keys) for c in audit['cells']) and all(v['passed'] for v in audit['old_evidence'].values()) and all(audit[k]['passed'] for k in ['old_unity_assets','unity_implementation']) and all(audit[k] for k in ['context_restored','ledger_accounted','no_logical_retries','local_cost_matches','within_cost_caps'])
    write(ROOT/'audit/results.json',audit);assert audit['passed'],'Inspect audit/results.json; do not change recorded outcomes'
    metrics={}
    for group in ['G2','G4']:
        rr=[r for r in s['results'] if r['group']==group];m={k:sum(bool(r[k]) for r in rr) for k in ['complete_success','state_success','normal_finish','initial_edit_failed','self_repaired','false_complete','process_protection_violation','final_protection_violation']}
        m.update(runs=4,no_report=sum(r['finish'] is None for r in rr),report_phase_entered=sum(bool(r['finalization']) for r in rr),
            flow_adherence=sum(bool(r['flow_adherence']) for r in rr) if group=='G4' else None,
            stop_reasons=dict(Counter(r['stop_reason'] for r in rr)),mean_seconds=statistics.mean(r['seconds'] for r in rr),
            stats={k:sum(r['stats'][k] for r in rr) for k in rr[0]['stats']})
        metrics[group]=m
    result=dict(time=timestamp(),completed=8,metrics=metrics,runs=rows,repairs=repairs,failure_categories=failures,
        engineering_acceptance=dict(all_actor_reports=all(r['normal_finish'] for r in s['results']),
            no_input_precheck_abandonment=all(r['stop_reason']!='input_budget_precheck' for r in s['results']),
            actual_report_phase_exercised=any(r['finalization'] for r in s['results'])),
        actual_feedback_bytes=dict(full=wire_full,lean=wire_lean,reduction_fraction=1-wire_lean/wire_full),
        local_ledger=s['ledger_totals'],global_local_upper=audit['global_totals'],audit_passed=True,
        interpretation='Different new development tasks; engineering verification only. Do not infer a causal cross-round success gain over the older formal batch.')
    write(ROOT/'development/analysis.json',result)
    with (ROOT/'development/runs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report(result,audit)
    print(json.dumps(dict(audit=True,metrics=metrics,feedback=result['actual_feedback_bytes'],global_upper=audit['global_totals']),ensure_ascii=False,indent=2))


def copy_dict(value):return dict(value)


def report(d,a):
    lines=['Check V3：精简反馈与收尾预算开发复验', '完成时间：'+d['time'], '',
        '本轮实现', '两组共同增加剩余输入/输出token与时间提醒，按完整历史的保守输入上界提前预留模型自己的finish及一次格式修正机会。总限额保持原样；不代写报告，不自动补检查或修复，不依据隐藏评分拒绝complete。',
        'G4仍执行全部公开规则，返回每一失败项的全部测量及预期，通过项仅汇总计数。compare_state保留全部实际变化。完整诊断另存供复查，不回传模型。在线判定与独立评分器文件保持原样。', '',
        '预检', '13项单元检查通过；4道新题实际Unity可行解、独立包围盒、保存重开与重置均通过；20个注入错误状态被识别。回放旧正式批次204个实际状态，失败细节全部保留，反馈UTF-8体积合计减少92.18%。这些工程预检不计入模型运行或修复。', '',
        '本轮8次实际模型开发运行']
    for g,m in d['metrics'].items():
        lines.append(f"{g}：完整成功{m['complete_success']}/4，最终场景达标{m['state_success']}/4，正常finish {m['normal_finish']}/4，无报告{m['no_report']}/4，首次失败后的场景自修复{m['self_repaired']}/{m['initial_edit_failed']}，错误complete声明{m['false_complete']}/4，提前报告阶段触发{m['report_phase_entered']}/4。")
        lines.append('终止原因：'+json.dumps(m['stop_reasons'],ensure_ascii=False))
    for row in d['runs']:
        lines.append(f"{row['run_id']}：完整成功={row['complete_success']}，场景达标={row['state_success']}，报告={row['finish_status']}，提前报告阶段={row['report_phase_entered']}；剩余失败规则：{row['failed_final_rules'] or '无'}")
    normal=sum(m['normal_finish'] for m in d['metrics'].values());abandon=sum(m['stop_reasons'].get('input_budget_precheck',0) for m in d['metrics'].values())
    lines += ['', '验收解读',f'8次中{normal}次正常提交模型自写报告；因input_budget_precheck直接停止{abandon}次。任务完成与正常报告分开计数，partial/failed不是任务成功保证。',
        f"实际G4检查反馈：原全量表示{d['actual_feedback_bytes']['full']}字节，精简表示{d['actual_feedback_bytes']['lean']}字节，减少{100*d['actual_feedback_bytes']['reduction_fraction']:.2f}%；所有失败细节均经对应实际状态回放核对。",
        '原正式48次中G4有19/24次因输入预算停止；本轮使用不同的新开发题，不能把两批成功率差直接归因于代码，也不是新的正式效果检验。剩余几何失败和错误完成声明全部保留。']
    state=read(ROOT/'development/D08_G4_r1/final_state.json');objects={o['id']:o for o in state['objects']}
    reference=read(ROOT/'preflight/D08/reference_state.json');refs={o['id']:o for o in reference['objects']}
    lines += ['', 'D08剩余失败的解释核验',
        f"D08Box1实际底面Y={objects['D08Box1']['bounds_min'][1]:.8f}，D08Left顶面Y={objects['D08Left']['bounds_max'][1]:.8f}，穿透约0.01米。支撑贴合容差0.01米，但非重叠穿透容差为0.001米，因此支持检查通过仍可能违反非重叠要求。",
        f"Unity预检可行解中，同一箱体底面Y={refs['D08Box1']['bounds_min'][1]:.8f}，与平台顶面相等，全部规则均通过。模型在partial报告中称支撑与非重叠存在逻辑冲突，这个解释不成立；它混淆了XZ投影重合和Y方向穿透。",
        '报告阶段正常触发并保留了真实失败，但有效partial报告不保证其失败解释正确。本轮没有把研究者可行解或事后修正计作模型修复，也没有继续补跑以得到全成功。', '', '资源与预算']
    for g,m in d['metrics'].items():
        v=m['stats'];lines.append(f"{g}：请求{v['requests']}，输入{v['input_tokens']} token，输出{v['output_tokens']} token，已知usage费用估算{v['cost_cny']:.6f}元，平均记录时长{m['mean_seconds']:.2f}秒。")
    lines += [f"本批账本占用（含未知请求完整预留）{d['local_ledger']['total']:.6f}元，上限15元。历史账本按request_id保守去重后累计上界{d['global_local_upper']['total']:.6f}元，上限300元，未确认请求共{d['global_local_upper']['unknown_requests']}个。", '费用沿用冻结单价按实际usage估算，不计缓存优惠；不能读取平台实际扣费及账本外消费，因此不是供应商账户余额。记录时长使用原harness的monotonic计时，另存wall_seconds；不据此作严格墙钟速度结论。', '',
        '保存与核验', '旧两轮开发和正式48次证据的文件哈希验证通过；旧正式Unity场景/元数据与共享脚本、项目依赖保持原样。全部新运行的初始状态、最终及中间评分、诊断、模型自写报告、token及账本均独立核验，Unity已恢复原场景。',
        '完整证据见development/各运行目录；逐运行数据见development/runs.csv，统计见development/analysis.json，核验见audit/results.json，启动前冻结见development/frozen_configuration.json。新场景仅使用check_v3d_命名空间。', '',
        '下一步', '本轮没有启动新的正式实验。下一版正式效果评估应在保留本批结果的基础上，提前冻结未参与调试的任务及分析计划；旧12题可作回归检查，不能作为全新的独立确认性任务。']
    (ROOT/'RESULTS.txt').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
