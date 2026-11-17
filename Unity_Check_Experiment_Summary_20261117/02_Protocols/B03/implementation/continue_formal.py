"""Continue only unstarted planned cells; never retry a recorded failed cell."""
import hashlib
import shutil
from common import ROOT, read, write, timestamp
from engine import Engine
from prepare import canonical
from provider import Client, Ledger, Lock
from run_development import run_cell
from run_formal import verify_freeze


def main():
    verify_freeze()
    previous = read(ROOT / 'formal/summary.json')
    assert previous['completed'] == 36 and previous['original_context_restored']
    saved = ROOT / 'formal/segments/segment_01_summary.json'
    assert not saved.exists()
    saved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'formal/summary.json', saved)
    shutil.copy2(ROOT / 'formal/progress.json', saved.parent / 'segment_01_progress.json')
    config = read(ROOT / 'config.json')
    schedule = read(ROOT / 'formal/schedule.json')['cells']
    results = previous['results']
    assert [r['run_id'] for r in results] == [c['run_id'] for c in schedule[:36]]
    assert all(not (ROOT / 'formal' / c['run_id']).exists() for c in schedule[36:])
    engine = Engine()
    context = engine.context()
    assert context == read(ROOT / 'formal/started.json')['original_context']
    ledger = Ledger(ROOT / 'cost_ledger.ndjson', config)
    client = Client(config, ledger)
    write(ROOT / 'formal/segments/segment_02_started.json', dict(time=timestamp(), reason='Continue 12 unstarted cells under the user-authorized 48-cell batch. Preserve W04_G2_r2 as a technical failure and retain its entire unknown reservation. No uncertain request or completed cell is retried.',
        completed_before=36, remaining=12, runtime_sha256=hashlib.sha256((ROOT / 'run_development.py').read_bytes()).hexdigest(),
        continuation_sha256=hashlib.sha256((ROOT / 'continue_formal.py').read_bytes()).hexdigest()))
    try:
        for cell in schedule[36:]:
            verify_freeze()
            write(ROOT / 'formal/active.json', dict(time=timestamp(), cell=cell, segment=2))
            task = read(ROOT / 'tasks' / (cell['task_id'] + '.json'))
            engine.reset(task, cell['run_id'] + '_initial')
            engine.decorate(task['contract'])
            initial = engine.save(cell['run_id'] + '_initial')
            assert canonical(initial) == canonical(read(ROOT / 'preflight' / cell['task_id'] / 'initial_state.json'))
            folder = ROOT / 'formal' / cell['run_id']
            result = run_cell(task, cell['group'], engine, client, config, folder, initial, seed=cell['seed'], stage='formal')
            result.update(repeat=cell['repeat'], seed=cell['seed'], block=cell['block'])
            write(folder / 'result.json', result)
            results.append(result)
            write(ROOT / 'formal/progress.json', dict(completed=results, planned=48, ledger_totals=ledger.totals(), segment=2))
            print('FORMAL', len(results), '/48', cell['run_id'], 'success', result['complete_success'], 'stop', result['stop_reason'], flush=True)
            if result['transport_failure']:
                break
    finally:
        engine.restore(context)
        write(ROOT / 'formal/summary.json', dict(time=timestamp(), planned=48, completed=len(results), results=results,
            ledger_totals=ledger.totals(), original_context_restored=engine.context() == context, development_runs=0,
            segments=2, uncertain_request_not_retried='W04_G2_r2_request_1'))


if __name__ == '__main__':
    with Lock(ROOT / 'unity_execution.lock'):
        main()
