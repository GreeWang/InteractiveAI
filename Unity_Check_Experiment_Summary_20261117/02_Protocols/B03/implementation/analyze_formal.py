"""Post-batch audit and prespecified task-level analysis. Never supplies agent input."""
import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path
from common import ROOT, read, write, timestamp
from engine import Engine
from offline_score import score
from online_check import check, compare
from prepare import canonical
from run_development import compact, initial_messages
from run_formal import verify_freeze


def ordered_flow(trace):
    edits = [i for i, e in enumerate(trace) if e.get('tool') == 'apply_edits' and 'error' not in e.get('observation', {})]
    for n, i in enumerate(edits):
        version = trace[i]['observation'].get('state_version')
        end = edits[n + 1] if n + 1 < len(edits) else len(trace)
        calls = [e['tool'] for e in trace[i + 1:end] if e.get('observation', {}).get('state_version') == version
                 and e.get('tool') in ['check_constraints', 'compare_state']]
        if calls[:2] != ['check_constraints', 'compare_state']:
            return False
    return bool(edits)


def percentile(values, fraction):
    values = sorted(values)
    index = (len(values) - 1) * fraction
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def bootstrap(values, seed, draws=10000):
    rng = random.Random(seed)
    means = [sum(rng.choice(values) for _ in values) / len(values) for _ in range(draws)]
    return [percentile(means, .025), percentile(means, .975)]


def file_manifest_ok(base, values):
    failures = [n for n, v in values.items() if not (base / n).is_file()
                or hashlib.sha256((base / n).read_bytes()).hexdigest() != v]
    return dict(checked=len(values), passed=not failures, failures=failures)


def main():
    summary = read(ROOT / 'formal/summary.json')
    schedule = read(ROOT / 'formal/schedule.json')['cells']
    assert summary['completed'] == summary['planned'] == len(schedule) == 48, 'Do not analyze an incomplete batch as complete'
    verify_freeze()
    config = read(ROOT / 'config.json')
    plan = read(ROOT / 'formal/analysis_plan.json')
    ledger = {e['request_id']: e for e in [json.loads(x) for x in (ROOT / 'cost_ledger.ndjson').read_text().splitlines()]}
    audit = dict(time=timestamp(), frozen_sources_match=True, original_context_restored=summary['original_context_restored'], cells=[])
    source = read(ROOT / 'source_round2_manifest.json')
    audit['round2_preservation'] = file_manifest_ok(Path(source['source']), source['sha256'])
    oldmanifest = read(Path(source['source']) / 'round1_preservation_manifest.json')
    audit['round1_preservation'] = file_manifest_ok(Path(oldmanifest['source']), oldmanifest['sha256'])
    scene_manifest = read(Path(source['source']) / 'round1_scene_preservation_manifest.json')
    audit['round1_scene_preservation'] = file_manifest_ok(Path('/'), scene_manifest['sha256'])
    audit['current_unity_context'] = Engine().context()
    audit['context_matches'] = audit['current_unity_context'] == read(ROOT / 'formal/started.json')['original_context']
    request_ids, results, records, repairs = set(), [], [], []
    failures = {'initial': {g: Counter() for g in ['G2', 'G4']}, 'final': {g: Counter() for g in ['G2', 'G4']}}
    for cell in schedule:
        folder = ROOT / 'formal' / cell['run_id']
        result = read(folder / 'result.json')
        assert result == next(r for r in summary['results'] if r['run_id'] == cell['run_id'])
        task = read(ROOT / 'tasks' / (cell['task_id'] + '.json'))
        contract = task['contract']
        initial, final = read(folder / 'initial_state.json'), read(folder / 'final_state.json')
        trace_path = folder / 'trace.ndjson'
        trace = [json.loads(x) for x in trace_path.read_text().splitlines()] if trace_path.exists() else []
        edit_states = [read(p) for p in sorted(folder.glob('after_edit_*.json'))]
        states = {s['state_version']: s for s in [initial] + edit_states}
        final_grade = score(final, initial, contract)
        grades = [score(s, initial, contract) for s in edit_states]
        prompts_match = read(folder / 'initial_context.json')['messages'] == initial_messages(task, cell['group'], initial, config)[0]
        diagnostics_match = True
        for e in trace:
            request_ids.add(e['request_id'])
            obs = e.get('observation', {})
            if e.get('tool') in ['check_constraints', 'compare_state'] and 'error' not in obs:
                state = states[obs['state_version']]
                expected = (check if e['tool'] == 'check_constraints' else compare)(state, initial, contract)
                expected.update(state_version=obs['state_version'], contract_version=contract['contract_version'])
                diagnostics_match &= compact(expected) == obs
        requests = [read(p) for p in sorted(folder.glob('request_*.json'))]
        responses = [read(p) for p in sorted(folder.glob('response_*.json'))]
        seed_model = all(p['seed'] == cell['seed'] and p['model'] == config['model']
                         and p['temperature'] == config['temperature'] and p['enable_thinking'] is False for p in requests)
        stats = result['stats']
        cell_ledger = [e for e in ledger.values() if e['key'].startswith(cell['run_id'] + '_request_')]
        unknown = [e for e in cell_ledger if e['status'] == 'reserved_unknown']
        request_ids.update(e['request_id'] for e in unknown)
        usage_ok = (stats['input_tokens'] == sum(p['usage']['prompt_tokens'] for p in responses)
                    and stats['output_tokens'] == sum(p['usage']['completion_tokens'] for p in responses)
                    and stats['requests'] == len(requests) == len(cell_ledger) == len(responses) + len(unknown)
                    and len(responses) == len(trace))
        estimated = sum(e['charged_upper_cny'] for e in cell_ledger if e['status'] == 'completed')
        flags_ok = (result['state_success'] == final_grade['success']
                    and result['complete_success'] == (result['normal_finish'] and final_grade['success'])
                    and result['initial_edit_failed'] == (bool(grades) and not grades[0]['success'])
                    and result['self_repaired'] == (bool(grades) and not grades[0]['success'] and final_grade['success'])
                    and result['false_complete'] == bool(result['finish'] and result['finish']['status'] == 'complete' and not final_grade['success'])
                    and result['process_protection_violation'] == any(g['protection_violation'] for g in grades)
                    and result['final_protection_violation'] == final_grade['protection_violation'])
        caps_ok = all(stats[k] <= config['limits'][k] for k in config['limits'] if k != 'seconds') and result['seconds'] <= config['limits']['seconds']
        item = dict(run_id=cell['run_id'], initial_matches_preflight=canonical(initial) == canonical(read(ROOT / 'preflight' / cell['task_id'] / 'initial_state.json')),
            metadata_matches=all(result[k] == cell[k] for k in ['run_id', 'task_id', 'group', 'repeat', 'seed', 'block']),
            independent_rescore_matches=final_grade == read(folder / 'offline_final_score.json') and all(g == read(folder / f'offline_edit_{i + 1:02}.json') for i, g in enumerate(grades)),
            flags_match=flags_ok, prompts_match=prompts_match, diagnostic_replay_matches=diagnostics_match,
            request_configuration_matches=seed_model, usage_matches=usage_ok, costs_match=math.isclose(estimated, stats['cost_cny'], abs_tol=1e-12), caps_passed=caps_ok,
            unknown_requests=[e['request_id'] for e in unknown],
            unknown_preserved_as_failure=(not unknown or (result['transport_failure'] == 'UnknownOutcome' and not result['complete_success'] and result['stop_reason'] == 'UnknownOutcome')),
            online_offline_final_agree=check(final, initial, contract)['passed'] == final_grade['success'],
            tool_errors=[dict(turn=e['turn'], tool=e.get('tool'), error=e['observation']) for e in trace if 'error' in e.get('observation', {})],
            ordered_flow=ordered_flow(trace) if cell['group'] == 'G4' else None,
            images_saved=all((folder / n).is_file() for n in ['final.png', 'final_top.png']))
        audit['cells'].append(item)
        result['ordered_flow'] = item['ordered_flow']
        result['edited'] = bool(grades)
        result['first_edit_success'] = grades[0]['success'] if grades else None
        result['evidence_timestamp_span_seconds'] = (folder / 'final_state.json').stat().st_mtime - (folder / 'request_01.json').stat().st_mtime
        results.append(result)
        initial_grade = grades[0] if grades else score(initial, initial, contract)
        for phase, grade in [('initial', initial_grade), ('final', final_grade)]:
            categories = {c['rule_id'].split(':')[0] for c in grade['checks'] if not c['passed']}
            failures[phase][cell['group']].update(categories)
        failed_final = [c['rule_id'] for c in final_grade['checks'] if not c['passed']]
        if result['self_repaired']:
            repairs.append(dict(run_id=cell['run_id'], failed_first=[c['rule_id'] for c in initial_grade['checks'] if not c['passed']],
                tools=[e.get('tool') for e in trace], edit_batches=stats['edit_batches'], final_success=True))
        records.append({**cell, **{k: result[k] for k in ['normal_finish', 'state_success', 'complete_success', 'initial_edit_failed', 'self_repaired', 'false_complete', 'flow_adherence', 'ordered_flow', 'process_protection_violation', 'final_protection_violation', 'stop_reason', 'seconds']},
            'finish_status': result['finish']['status'] if result['finish'] else 'no_report',
            'edited': result['edited'], 'first_edit_success': result['first_edit_success'],
            'evidence_timestamp_span_seconds': result['evidence_timestamp_span_seconds'],
            **stats, 'failed_final_rules': ';'.join(failed_final)})
    exceptions = read(ROOT / 'audit/unknown_request_exceptions.json')['exceptions'] if (ROOT / 'audit/unknown_request_exceptions.json').exists() else []
    unresolved = [e for e in ledger.values() if e['status'] == 'reserved_unknown']
    accounted = all(e['status'] == 'completed' or any(x['request_id'] == e['request_id'] and x['scope'] == 'formal'
        and x['preserve_full_reservation'] and x['user_authorization'] and math.isclose(x['reserved_cny'], e['charged_upper_cny'], abs_tol=1e-12) for x in exceptions) for e in ledger.values())
    audit['ledger'] = dict(requests=len(ledger), all_completed=all(e['status'] == 'completed' for e in ledger.values()),
        all_accounted=accounted, completed_requests=sum(e['status'] == 'completed' for e in ledger.values()),
        unknown_requests=len(unresolved), unknown_request_ids=[e['request_id'] for e in unresolved],
        logical_request_keys_unique=len({e['key'] for e in ledger.values()}) == len(ledger),
        known_token_estimate_cny=sum(e['charged_upper_cny'] for e in ledger.values() if e['status'] == 'completed'),
        uncertain_reserved_upper_cny=sum(e['charged_upper_cny'] for e in unresolved),
        all_formal=all(e['stage'] == 'formal' for e in ledger.values()), request_ids_match=request_ids == set(ledger),
        estimated_cny=sum(e['charged_upper_cny'] for e in ledger.values()))
    audit['ledger']['summary_matches'] = math.isclose(audit['ledger']['estimated_cny'], summary['ledger_totals']['total'], abs_tol=1e-12)
    audit['planned_cells_match'] = len(results) == 48 and len({r['run_id'] for r in results}) == 48
    audit['paired_initial_states_identical'] = all(len({canonical(read(ROOT / 'formal' / c['run_id'] / 'initial_state.json')) for c in schedule if c['task_id'] == tid}) == 1 for tid in read(ROOT / 'task_manifest.json')['formal'])
    audit['timestamp_gap_over_five_seconds'] = [r['run_id'] for r in results if r['evidence_timestamp_span_seconds'] - r['seconds'] > 5]
    factual_keys = ['initial_matches_preflight', 'metadata_matches', 'independent_rescore_matches', 'flags_match', 'prompts_match',
                    'diagnostic_replay_matches', 'request_configuration_matches', 'usage_matches', 'costs_match', 'images_saved', 'unknown_preserved_as_failure']
    audit['passed'] = all(audit[k]['passed'] for k in ['round2_preservation', 'round1_preservation', 'round1_scene_preservation']) and all(
        all(c[k] for k in factual_keys) for c in audit['cells']) and all(audit['ledger'][k] for k in ['all_accounted', 'all_formal', 'request_ids_match', 'summary_matches', 'logical_request_keys_unique']) and all(
        audit[k] for k in ['context_matches', 'original_context_restored', 'planned_cells_match', 'paired_initial_states_identical'])
    write(ROOT / 'analysis/audit.json', audit)
    if not audit['passed']:
        raise RuntimeError('Evidence audit failed; inspect analysis/audit.json without altering formal results')
    metrics = {}
    flags = ['complete_success', 'state_success', 'normal_finish', 'false_complete', 'initial_edit_failed', 'self_repaired', 'final_protection_violation', 'process_protection_violation']
    for group in ['G2', 'G4']:
        rs = [r for r in results if r['group'] == group]
        d = {k: sum(bool(r[k]) for r in rs) for k in flags}
        d.update(planned=24, complete_claims=sum(bool(r['finish'] and r['finish']['status'] == 'complete') for r in rs),
            uncertain_reserved_upper_cny=sum(e['charged_upper_cny'] for e in unresolved if f'_{group}_' in e['key']),
            technical_failures=sum(bool(r['transport_failure']) for r in rs),
            no_report=sum(r['finish'] is None for r in rs),
            stop_reasons=dict(Counter(r['stop_reason'] for r in rs)),
            flow_gap_budget_stop=sum(r['flow_adherence'] is False and r['stop_reason'] in ['input_budget_precheck', 'output_budget', 'request_limit', 'time_limit', 'time_limit_after_model', 'tool_limit'] for r in rs) if group == 'G4' else None,
            flow_gap_valid_finish=sum(r['flow_adherence'] is False and r['normal_finish'] for r in rs) if group == 'G4' else None,
            edited=sum(r['edited'] for r in rs), first_edit_success=sum(r['first_edit_success'] is True for r in rs),
            flow_adherence=sum(bool(r['flow_adherence']) for r in rs) if group == 'G4' else None,
            ordered_flow=sum(bool(r['ordered_flow']) for r in rs) if group == 'G4' else None,
            tool_errors=sum(len(c['tool_errors']) for c in audit['cells'] if f'_{group}_' in c['run_id']),
            caps_exceeded=sum(not c['caps_passed'] for c in audit['cells'] if f'_{group}_' in c['run_id']),
            mean_seconds=statistics.mean(r['seconds'] for r in rs), median_seconds=statistics.median(r['seconds'] for r in rs),
            mean_evidence_timestamp_span_seconds=statistics.mean(r['evidence_timestamp_span_seconds'] for r in rs),
            stats={k: sum(r['stats'][k] for r in rs) for k in rs[0]['stats']})
        metrics[group] = d
    tasks = []
    for tid in read(ROOT / 'task_manifest.json')['formal']:
        groups = {g: [r for r in results if r['task_id'] == tid and r['group'] == g] for g in ['G2', 'G4']}
        row = dict(task_id=tid)
        for g, rs in groups.items():
            row[g] = dict(success=sum(r['complete_success'] for r in rs), initial_success=sum(r['first_edit_success'] is True for r in rs),
                repairs=sum(r['self_repaired'] for r in rs), false_complete=sum(r['false_complete'] for r in rs),
                mean_seconds=statistics.mean(r['seconds'] for r in rs), input_tokens=sum(r['stats']['input_tokens'] for r in rs),
                output_tokens=sum(r['stats']['output_tokens'] for r in rs), cost_cny=sum(r['stats']['cost_cny'] for r in rs))
        row['success_difference'] = (row['G4']['success'] - row['G2']['success']) / 2
        tasks.append(row)
    families = []
    for name, ids in plan['families'].items():
        families.append(dict(family=name, tasks=ids, **{g: sum(t[g]['success'] for t in tasks if t['task_id'] in ids) for g in ['G2', 'G4']},
            success_difference=statistics.mean(t['success_difference'] for t in tasks if t['task_id'] in ids)))
    diffs = [t['success_difference'] for t in tasks]
    pairs = Counter()
    for c in schedule[::2]:
        pair = {r['group']: r['complete_success'] for r in results if r['task_id'] == c['task_id'] and r['repeat'] == c['repeat']}
        pairs['both_success' if all(pair.values()) else 'both_failure' if not any(pair.values()) else 'G4_only_success' if pair['G4'] else 'G2_only_success'] += 1
    analysis = dict(time=timestamp(), planned=48, completed=48, metrics=metrics, tasks=tasks, families=families,
        primary_effect=dict(task_mean_difference=statistics.mean(diffs), task_bootstrap_95=bootstrap(diffs, plan['bootstrap']['seed']),
            family_bootstrap_95=bootstrap([f['success_difference'] for f in families], plan['bootstrap']['seed']),
            improved_tasks=sum(d > 0 for d in diffs), unchanged_tasks=sum(d == 0 for d in diffs), worse_tasks=sum(d < 0 for d in diffs)),
        paired_run_outcomes=dict(pairs), failure_categories=failures, repairs=repairs,
        cost_estimate_cny=audit['ledger']['known_token_estimate_cny'], cost_with_unknown_reservations_upper_cny=audit['ledger']['estimated_cny'],
        technical_failure_cells=[r['run_id'] for r in results if r['transport_failure']],
        actual_billed_cost_available=False, audit_passed=True)
    affected_blocks = {r['block'] for r in results if r['transport_failure']}
    analysis['infrastructure_sensitivity'] = dict(note='Supplement only: remove entire affected paired blocks, retain primary denominator 24 per condition',
        excluded_blocks=sorted(affected_blocks), **{g: dict(success=sum(r['complete_success'] for r in results if r['group'] == g and r['block'] not in affected_blocks),
        denominator=sum(r['group'] == g and r['block'] not in affected_blocks for r in results),
        mean_seconds=statistics.mean(r['seconds'] for r in results if r['group'] == g and r['block'] not in affected_blocks),
        input_tokens=sum(r['stats']['input_tokens'] for r in results if r['group'] == g and r['block'] not in affected_blocks),
        cost_cny=sum(r['stats']['cost_cny'] for r in results if r['group'] == g and r['block'] not in affected_blocks)) for g in ['G2', 'G4']})
    write(ROOT / 'analysis/results.json', analysis)
    with (ROOT / 'analysis/runs.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    print(json.dumps(dict(audit=True, metrics=metrics, primary_effect=analysis['primary_effect'], pairs=pairs,
        families=families, failure_categories=failures, cost_cny=analysis['cost_estimate_cny']), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
