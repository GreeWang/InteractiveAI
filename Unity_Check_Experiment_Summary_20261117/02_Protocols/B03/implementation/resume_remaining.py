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
    assert 0 < previous['completed'] < 48 and previous['original_context_restored']
    start = previous['completed']
    segment = previous.get('segments', 1) + 1
    saved = ROOT / f'formal/segments/segment_{segment-1:02}_summary.json'
    assert not saved.exists()
    saved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'formal/summary.json', saved)
    shutil.copy2(ROOT / 'formal/progress.json', saved.parent / f'segment_{segment-1:02}_progress.json')
    config = read(ROOT / 'config.json')
    schedule = read(ROOT / 'formal/schedule.json')['cells']
    results = previous['results']
    assert [r['run_id'] for r in results] == [c['run_id'] for c in schedule[:start]]
    assert all(not (ROOT / 'formal' / c['run_id']).exists() for c in schedule[start:])
    engine = Engine()
    context = engine.context()
    assert context == read(ROOT / 'formal/started.json')['original_context']
    ledger = Ledger(ROOT / 'cost_ledger.ndjson', config)
    client = Client(config, ledger)
    write(ROOT / f'formal/segments/segment_{segment:02}_started.json', dict(time=timestamp(), reason='Continue only unstarted original cells under the user-authorized 48-cell batch. Every recorded technical failure and full unknown reservation remain. No uncertain request or completed cell is retried.',
        completed_before=start, remaining=48-start, runtime_sha256=hashlib.sha256((ROOT / 'run_development.py').read_bytes()).hexdigest(),
        continuation_sha256=hashlib.sha256((ROOT / 'resume_remaining.py').read_bytes()).hexdigest()))
    try:
        for cell in schedule[start:]:
            verify_freeze()
            write(ROOT / 'formal/active.json', dict(time=timestamp(), cell=cell, segment=segment))
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
            write(ROOT / 'formal/progress.json', dict(completed=results, planned=48, ledger_totals=ledger.totals(), segment=segment))
            print('FORMAL', len(results), '/48', cell['run_id'], 'success', result['complete_success'], 'stop', result['stop_reason'], flush=True)
            if result['transport_failure']:
                break
    finally:
        engine.restore(context)
        write(ROOT / 'formal/summary.json', dict(time=timestamp(), planned=48, completed=len(results), results=results,
            ledger_totals=ledger.totals(), original_context_restored=engine.context() == context, development_runs=0,
            segments=segment, uncertain_requests_not_retried=True))


if __name__ == '__main__':
    with Lock(ROOT / 'unity_execution.lock'):
        main()
