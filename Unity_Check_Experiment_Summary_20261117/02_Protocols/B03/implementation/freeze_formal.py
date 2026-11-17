"""Pre-outcome formal freeze, with inherited real-Unity gates and source hashes."""
import hashlib
from pathlib import Path
from common import ROOT, read, write, timestamp
from run_formal import make_schedule
from run_development import initial_messages


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (ROOT / 'formal/frozen_configuration.json').exists():
        raise RuntimeError('Already frozen')
    source = ROOT.parent / 'check_v2_round2'
    manifest = read(ROOT / 'source_round2_manifest.json')['sha256']
    assert all(sha(source / n) == v for n, v in manifest.items())
    gate = read(ROOT / 'preflight/summary.json')
    feedback = read(ROOT / 'preflight/round2_feedback_validation.json')
    assert gate['passed'] and gate['formal_count'] == 12 and gate['model_calls'] == 0
    assert feedback['passed'] and feedback['regression_snapshots'] == 98
    for name in ['online_check.py', 'offline_score.py', 'provider.py', 'common.py']:
        assert sha(ROOT / name) == sha(source / name)
    for subdir, suffix in [('tasks', '*.json'), ('skills', '*.md')]:
        for p in (ROOT / subdir).glob(suffix):
            assert sha(p) == sha(source / p.relative_to(ROOT))
    assert 'Ran 10 tests' in (ROOT / 'formal_tests.log').read_text()
    assert (ROOT / 'formal_tests.log').read_text().rstrip().endswith('OK')
    config = read(ROOT / 'config.json')
    ids = read(ROOT / 'task_manifest.json')['formal']
    schedule = make_schedule(ids, config['order_seed'])
    write(ROOT / 'formal/schedule.json', dict(time=timestamp(), seed=config['order_seed'], cells=schedule,
        first_condition_counts={'G2': 12, 'G4': 12}, paired_blocks=24, planned=48))
    families = {'M_layout': ['M01', 'M02'], 'M_dynamic_facing': ['M03', 'M04'],
                'M_permissions': ['M05', 'M06'], 'W_packing': ['W01', 'W02'],
                'W_support': ['W03', 'W04'], 'W_rotation_footprint': ['W05', 'W06']}
    write(ROOT / 'formal/analysis_plan.json', dict(time=timestamp(), frozen_before_model_calls=True,
        primary='complete_success: valid normal finish within budgets and independently scored final state satisfying every target and permission',
        denominator={'G2': 24, 'G4': 24}, statistical_unit='task; average two repeats within each task and condition',
        effect='mean of twelve paired task success differences G4-G2',
        bootstrap=dict(draws=10000, seed=20261116, resample_unit='whole task with both conditions and repeats', confidence=.95, interval='percentile; exploratory, conditional on these fixed tasks'),
        family_sensitivity='additional bootstrap of six whole families; descriptive due only six related families',
        families=families, secondary=['state_success', 'false_complete', 'complete_claims', 'initial_edit_failed',
            'self_repaired conditional on initially failed edit', 'final/process protection_violation',
            'flow_adherence for every edited version', 'ordered_flow before next edit or finish',
            'requests/tools/edit batches/token usage/estimated CNY/seconds', 'initial/final failed rule categories'],
        missing_or_technical_failure='retain planned cell as main-endpoint failure; list reason and show any infrastructure-only sensitivity separately',
        exclusions='No developer runs or researcher preflight corrections counted; no optional stopping or success-based reruns',
        attribution='effect of the Check package (skill + diagnostics + workflow reminders) under equal resource caps; components cannot be separated',
        retry_policy='frozen development transport: no automatic retry; unknown billable outcomes halt spending with reservation retained',
        limitations='12 fixed related tasks, two API repeats each, model seed accepted but reproducibility not guaranteed; no human-study outcomes'))
    for tid in ids:
        task = read(ROOT / 'tasks' / (tid + '.json'))
        initial = read(ROOT / 'preflight' / tid / 'initial_state.json')
        for group in ['G2', 'G4']:
            messages, skills = initial_messages(task, group, initial, config)
            write(ROOT / 'formal/prompt_templates' / (tid + '_' + group + '.json'), dict(messages=messages, loaded_skills=skills))
    write(ROOT / 'formal/readiness.json', dict(time=timestamp(), passed=True, tests=10,
        round2_preserved_files=len(manifest), actual_unity_preflight_inherited=True, feedback_regression_snapshots=98,
        formal_model_calls_before_freeze=0, note='Existing actual Unity preflight and signed-feedback engineering validation inherited without changing tasks or predicates. Each formal reset is checked against its recorded actual initial snapshot before model calls.'))
    source_files = list(ROOT.glob('*.py')) + list((ROOT / 'skills').glob('*.md')) + list((ROOT / 'tasks').glob('*.json'))
    source_files += list((ROOT / 'preflight').rglob('*.json')) + list((ROOT / 'formal').rglob('*.json'))
    source_files += [ROOT / n for n in ['config.json', 'task_manifest.json', 'formal_tests.log', 'source_round2_manifest.json']]
    project = Path(config['project'])
    project_files = list((project / 'Assets/P2SCV1').rglob('*.cs'))
    project_files += [project / 'ProjectSettings/ProjectVersion.txt', project / 'Packages/manifest.json', project / 'Packages/packages-lock.json']
    frozen = dict(time=timestamp(), scope='48 formal cells; frozen round2 Check package, same independent scorer and same execution caps',
        sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(set(source_files))},
        project_sha256={str(p): sha(p) for p in project_files})
    write(ROOT / 'formal/frozen_configuration.json', frozen)
    print('FROZEN', len(frozen['sha256']), 'files;', len(frozen['project_sha256']), 'Unity sources/settings;', len(schedule), 'planned cells')


if __name__ == '__main__':
    main()
