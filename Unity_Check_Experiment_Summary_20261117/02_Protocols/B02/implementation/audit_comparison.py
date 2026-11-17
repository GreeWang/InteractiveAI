"""Read-only post-run audit; creates reports only, with no model or scene writes."""
import hashlib
import json
import math
from pathlib import Path
from common import ROOT, read, write, timestamp
from offline_score import score
from online_check import check
from prepare import canonical
from engine import Engine


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def preserved(base, manifest):
    failures = [name for name, expected in manifest.items()
                if not (base / name).is_file() or sha(base / name) != expected]
    return dict(checked=len(manifest), passed=not failures, failures=failures)


def ordered_flow(trace):
    edits = [i for i, e in enumerate(trace) if e.get('tool') == 'apply_edits']
    for n, i in enumerate(edits):
        version = trace[i]['observation'].get('state_version')
        end = edits[n + 1] if n + 1 < len(edits) else len(trace)
        matching = [e['tool'] for e in trace[i + 1:end]
                    if e.get('observation', {}).get('state_version') == version
                    and e.get('tool') in ['check_constraints', 'compare_state']]
        if matching[:2] != ['check_constraints', 'compare_state']:
            return False
    return bool(edits)


def aggregate(results):
    out = {}
    for group in ['G2', 'G4']:
        rs = [r for r in results if r['group'] == group]
        d = {k: sum(bool(r[k]) for r in rs) for k in [
            'complete_success', 'normal_finish', 'false_complete', 'initial_edit_failed',
            'self_repaired', 'final_protection_violation', 'process_protection_violation']}
        d.update(runs=len(rs), complete_claims=sum(r['finish']['status'] == 'complete' for r in rs),
                 flow_adherence=sum(bool(r['flow_adherence']) for r in rs) if group == 'G4' else None,
                 mean_seconds=sum(r['seconds'] for r in rs) / len(rs))
        d['stats'] = {k: sum(r['stats'][k] for r in rs) for k in rs[0]['stats']}
        out[group] = d
    return out


def main():
    old = Path(read(ROOT / 'round1_preservation_manifest.json')['source'])
    audit = dict(time=timestamp())
    audit['round1_files'] = preserved(old, read(ROOT / 'round1_preservation_manifest.json')['sha256'])
    audit['round1_scene_files'] = preserved(Path('/'), read(ROOT / 'round1_scene_preservation_manifest.json')['sha256'])
    audit['frozen_round2_files'] = preserved(ROOT, read(ROOT / 'development/frozen_configuration.json')['sha256'])
    unchanged = ['offline_score.py', 'skills/unity-scene-ops.md'] + [str(p.relative_to(ROOT)) for p in (ROOT / 'tasks').glob('*.json')]
    audit['unchanged_tasks_scorer_shared_skill'] = preserved(ROOT, {name: sha(old / name) for name in unchanged})
    a, b = read(old / 'config.json'), read(ROOT / 'config.json')
    audit['configuration_only_version_changed'] = {k: v for k, v in a.items() if k != 'version'} == {k: v for k, v in b.items() if k != 'version'}
    s1, s2 = read(old / 'development/summary.json'), read(ROOT / 'development/summary.json')
    audit['eight_unique_planned_cells'] = s2['completed'] == 8 and sorted(r['run_id'] for r in s2['results']) == sorted(c['run_id'] for c in read(ROOT / 'development/schedule.json')['cells'])
    audit['same_schedule'] = read(old / 'development/schedule.json')['cells'] == read(ROOT / 'development/schedule.json')['cells']
    audit['formal_runs'] = s2['formal_runs']
    audit['original_context_restored'] = s2['original_context_restored']
    audit['current_unity_context'] = Engine().context()
    audit['current_context_matches'] = audit['current_unity_context'] == dict(active=b['original_scene'], dirty=False, count=1)
    audit['cells'] = []
    ledger = [json.loads(x) for x in (ROOT / 'cost_ledger.ndjson').read_text().splitlines()]
    latest = {e['request_id']: e for e in ledger}
    expected_request_ids = set()
    repair_evidence = []
    for r in s2['results']:
        folder = ROOT / 'development' / r['run_id']
        initial, final = read(folder / 'initial_state.json'), read(folder / 'final_state.json')
        contract = read(ROOT / 'tasks' / (r['task_id'] + '.json'))['contract']
        trace = [json.loads(x) for x in (folder / 'trace.ndjson').read_text().splitlines()]
        expected_request_ids.update(e['request_id'] for e in trace)
        graded = score(final, initial, contract)
        edit_paths = sorted(folder.glob('after_edit_*.json'))
        process_grades = [score(read(p), initial, contract) for p in edit_paths]
        stats = r['stats']
        caps = b['limits']
        budgets = all(stats[k] <= caps[k] for k in caps if k != 'seconds') and r['seconds'] <= caps['seconds']
        responses = [read(p) for p in sorted(folder.glob('response_*.json'))]
        requests = sorted(folder.glob('request_*.json'))
        tokens_match = stats['input_tokens'] == sum(x['usage']['prompt_tokens'] for x in responses) and stats['output_tokens'] == sum(x['usage']['completion_tokens'] for x in responses)
        requests_match = stats['requests'] == len(requests) == len(responses) == len(trace)
        cost = sum(latest[e['request_id']]['charged_upper_cny'] for e in trace)
        errors = [e['turn'] for e in trace if 'error' in e.get('observation', {})]
        offline_match = graded == read(folder / 'offline_final_score.json') and all(g == read(folder / f'offline_edit_{i + 1:02}.json') for i, g in enumerate(process_grades))
        flags_match = (r['state_success'] == graded['success']
                       and r['complete_success'] == (r['normal_finish'] and graded['success'])
                       and r['initial_edit_failed'] == (bool(process_grades) and not process_grades[0]['success'])
                       and r['self_repaired'] == (bool(process_grades) and not process_grades[0]['success'] and graded['success'])
                       and r['false_complete'] == (r['finish']['status'] == 'complete' and not graded['success']))
        control_identical = None
        if r['group'] == 'G2':
            control_identical = read(folder / 'request_01.json')['messages'] == read(old / 'development' / r['run_id'] / 'request_01.json')['messages']
        audit['cells'].append(dict(run_id=r['run_id'], normal_finish=r['normal_finish'], budgets_passed=budgets,
            tokens_match=tokens_match, requests_match=requests_match, costs_match=math.isclose(cost, stats['cost_cny'], abs_tol=1e-12),
            errors=errors, offline_rescore_match=offline_match, flags_match=flags_match,
            online_offline_agree=check(final, initial, contract)['passed'] == graded['success'],
            initial_matches_preflight=canonical(initial) == canonical(read(ROOT / 'preflight' / r['task_id'] / 'initial_state.json')),
            ordered_flow=ordered_flow(trace) if r['group'] == 'G4' else None, control_first_request_identical=control_identical))
        if r['self_repaired']:
            first = process_grades[0]
            repair_evidence.append(dict(run_id=r['run_id'], first_failed_rules=[c['rule_id'] for c in first['checks'] if not c['passed']],
                first_facing_errors={c['rule_id']: c['measurement']['angle'] for c in first['checks'] if c['rule_id'].startswith('facing:')},
                final_facing_errors={c['rule_id']: c['measurement']['angle'] for c in graded['checks'] if c['rule_id'].startswith('facing:')},
                tool_sequence=[e.get('tool') for e in trace], final_success=graded['success']))
    audit['ledger'] = dict(requests=len(latest), all_completed=all(e['status'] == 'completed' for e in latest.values()),
        ids_match=set(latest) == expected_request_ids, all_pilot=all(e['stage'] == 'pilot' for e in latest.values()),
        estimated_cny=sum(e['charged_upper_cny'] for e in latest.values()))
    audit['ledger']['summary_matches'] = math.isclose(audit['ledger']['estimated_cny'], s2['ledger_totals']['total'], abs_tol=1e-12)
    checks = [audit[k]['passed'] for k in ['round1_files', 'round1_scene_files', 'frozen_round2_files', 'unchanged_tasks_scorer_shared_skill']]
    checks += [audit[k] for k in ['configuration_only_version_changed', 'eight_unique_planned_cells', 'same_schedule', 'original_context_restored', 'current_context_matches']]
    checks += [audit['formal_runs'] == 0, *[audit['ledger'][k] for k in ['all_completed', 'ids_match', 'all_pilot', 'summary_matches']]]
    for cell in audit['cells']:
        checks += [cell[k] for k in ['normal_finish', 'budgets_passed', 'tokens_match', 'requests_match', 'costs_match', 'offline_rescore_match', 'flags_match', 'online_offline_agree', 'initial_matches_preflight']]
        checks += [not cell['errors'], cell['ordered_flow'] is not False, cell['control_first_request_identical'] is not False]
    audit['passed'] = all(checks)
    write(ROOT / 'development/audit.json', audit)
    ag1, ag2 = aggregate(s1['results']), aggregate(s2['results'])
    comparison = dict(time=timestamp(), round1=ag1, round2=ag2, repairs=repair_evidence, audit_passed=audit['passed'],
        task_outcomes=[dict(task_id=t, **{label: {g: next(r['complete_success'] for r in s['results'] if r['task_id'] == t and r['group'] == g) for g in ['G2', 'G4']} for label, s in [('round1', s1), ('round2', s2)]}) for t in ['D01', 'D02', 'D03', 'D04']],
        interpretation='Development evidence only; four reused tasks, one cell per group and task in each round. Feedback and workflow reminders changed together. Not an independent confirmatory study or an estimate of general effect size.')
    write(ROOT / 'development/comparison.json', comparison)
    print(json.dumps(dict(audit_passed=audit['passed'], preserved=audit['round1_files']['checked'], scene_preserved=audit['round1_scene_files']['checked'], round1=ag1, round2=ag2, ledger=audit['ledger'], repairs=repair_evidence), ensure_ascii=False, indent=2))
    if not audit['passed']:
        raise RuntimeError('Audit failed; inspect development/audit.json')


if __name__ == '__main__':
    main()
