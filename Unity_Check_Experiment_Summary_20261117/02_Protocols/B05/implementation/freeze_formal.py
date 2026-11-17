"""Lock the new task instances and task-level analysis before any model calls."""
import hashlib
from pathlib import Path
from common import ROOT,read,write,timestamp
from run_formal import make_schedule
from run_development import initial_messages
from provider import Ledger


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (ROOT/'formal/frozen_configuration.json').exists()
    pre=read(ROOT/'preflight/summary.json');assert pre['passed'] and len(pre['records'])==12 and pre['model_calls']==0
    assert (ROOT/'unit_tests.log').read_text().rstrip().endswith('OK') and 'Ran 17 tests' in (ROOT/'unit_tests.log').read_text()
    source=read(ROOT/'audit/source_v3_preservation.json');assert all(sha(Path(source['source'])/n)==v for n,v in source['sha256'].items())
    cfg=read(ROOT/'config.json');manifest=read(ROOT/'task_manifest.json');cells=make_schedule(manifest['formal'],cfg['order_seed'])
    write(ROOT/'formal/schedule.json',dict(time=timestamp(),seed=cfg['order_seed'],cells=cells,paired_blocks=24,G2_first=12,G4_first=12))
    write(ROOT/'formal/analysis_plan.json',dict(time=timestamp(),frozen_before_formal_calls=True,formal_task_ids=manifest['formal'],
        primary='complete_success: normal valid actor-written finish within caps AND independently scored final state passing all targets and permissions; finish status need not say complete',
        denominator={'G2':24,'G4':24},statistical_unit='task; average two repeats per condition, then take twelve paired G4-G2 differences',
        bootstrap=dict(draws=10000,seed=2026111603,unit='whole task, preserving both groups and repeats',confidence=.95,method='percentile exploratory interval'),
        families=manifest['families'],family_sensitivity='Resample six whole task families; descriptive due only six related families',
        secondary=['state_success','normal_finish','no_report','false_complete','complete_claims','first_edit_success','self_repaired given first edit failure',
            'process/final protection violation','flow adherence and ordered coverage','report-phase entry','requests/tools/edits/input-output tokens/estimated cost/recorded time','initial/final rule-failure categories'],
        technical_failure='Retain in fixed main denominator as failure; optionally remove entire affected paired blocks for supplementary sensitivity; do not replace cells',
        retry='No automatic transport retry; retain full unknown reservation and continue only original unstarted cells under the existing authorization and caps',
        runtime='V3 actor, compact feedback and resource reserve are byte-identical to passed development version; both groups share budget reminders and caps',
        attribution='Check package: additional guide, diagnostics and workflow reminders. No isolated component effect can be inferred.',
        scope='12 new geometric task instances within six previously used task families, built after earlier results; no formal model calls before freezing. Not an independently sampled universal benchmark.',
        cross_version='V2 and V3 formal batches use different tasks; compare within-batch G2/G4. Cross-version rates are descriptive only.',
        timing='Original monotonic duration plus recorded wall_seconds. Timing discrepancies or technical stalls must be disclosed; do not equate failed-run duration with successful completion time.',
        human_study='No participant outcomes collected by this automated batch',budget={'local_batch_cny':15,'aggregate_local_cny':300}))
    for tid in manifest['formal']:
        t=read(ROOT/'tasks'/(tid+'.json'));initial=read(ROOT/'preflight'/tid/'initial_state.json')
        for g in ['G2','G4']:
            messages,skills=initial_messages(t,g,initial,cfg);write(ROOT/'formal/prompt_templates'/(tid+'_'+g+'.json'),dict(messages=messages,loaded_skills=skills))
    old_roots=['check_v2_execution','check_v2_round2','check_v2_formal','check_v3_development'];old={}
    for name in old_roots:
        root=ROOT.parent/name;p=root/'results_preservation_manifest.json'
        m=read(p)['sha256'] if p.exists() else {str(x.relative_to(root)):sha(x) for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts}
        assert all(sha(root/n)==v for n,v in m.items()),name;old[str(root)]=m
    write(ROOT/'audit/previous_evidence_manifest.json',old)
    ledger=Ledger(ROOT/'cost_ledger.ndjson',cfg);write(ROOT/'audit/prior_cost_snapshot.json',dict(time=timestamp(),global_totals=ledger.global_totals(),basis='Conservative request-ID deduplication with full unknown reservations; provider account statement unavailable'))
    write(ROOT/'formal/readiness.json',dict(time=timestamp(),passed=True,unit_tests=17,actual_unity_tasks=12,
        negative_cases=sum(r['negatives'] for r in pre['records']),model_calls_before_freeze=0,original_context_restored=pre['original_context_restored']))
    files=[p for p in ROOT.glob('*.py') if p.name!='analyze_formal.py']+list((ROOT/'skills').glob('*.md'))+list((ROOT/'tasks').glob('*.json'))+list((ROOT/'preflight').rglob('*.json'))+list((ROOT/'formal').rglob('*.json'))+list((ROOT/'audit').glob('*.json'))
    files += [ROOT/x for x in ['config.json','task_design.json','task_manifest.json','unit_tests.log','TASKS.txt']]
    project=Path(cfg['project']);project_files=list((project/'Assets/P2SCV1').rglob('*.cs'))+[project/'ProjectSettings/ProjectVersion.txt',project/'Packages/manifest.json',project/'Packages/packages-lock.json']
    write(ROOT/'formal/frozen_configuration.json',dict(time=timestamp(),sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))},project_sha256={str(p):sha(p) for p in project_files}))
    print('Frozen',len(set(files)),'files, 48 planned cells; prior local cost upper',ledger.global_totals()['total'])


if __name__=='__main__':main()
