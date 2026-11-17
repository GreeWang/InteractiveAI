"""Frozen 12-task x 2-condition x 2-repeat serial formal batch."""
import hashlib
import random
from common import ROOT, read, write, timestamp
from engine import Engine
from prepare import canonical
from provider import Client, Ledger, Lock
from run_development import run_cell


def make_schedule(task_ids, seed):
    rng = random.Random(seed)
    blocks = [(tid, repeat) for tid in task_ids for repeat in [1, 2]]
    rng.shuffle(blocks)
    orders = [['G2', 'G4']] * 12 + [['G4', 'G2']] * 12
    rng.shuffle(orders)
    return [dict(block=i + 1, task_id=tid, repeat=repeat, seed=repeat,
                 group=group, run_id=f'{tid}_{group}_r{repeat}')
            for i, ((tid, repeat), order) in enumerate(zip(blocks, orders))
            for group in order]


def verify_freeze():
    frozen = read(ROOT / 'formal/frozen_configuration.json')
    for name, expected in frozen['sha256'].items():
        path = ROOT / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Frozen file changed: ' + name)
    for name, expected in frozen['project_sha256'].items():
        from pathlib import Path
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Frozen Unity implementation changed: ' + name)


def main():
    verify_freeze()
    gate = read(ROOT / 'formal/readiness.json')
    if not gate['passed']:
        raise RuntimeError('Formal readiness gate failed')
    config = read(ROOT / 'config.json')
    schedule = read(ROOT / 'formal/schedule.json')['cells']
    if (ROOT / 'formal/started.json').exists():
        raise RuntimeError('Batch already started; preserve attempts and inspect before resuming')
    engine = Engine()
    context = engine.context()
    if context['dirty'] or context['count'] != 1:
        raise RuntimeError('Original Unity context must be clean and single-scene')
    ledger = Ledger(ROOT / 'cost_ledger.ndjson', config)
    client = Client(config, ledger)
    write(ROOT / 'formal/started.json', dict(time=timestamp(), original_context=context))
    results = []
    try:
        for cell in schedule:
            verify_freeze()
            folder = ROOT / 'formal' / cell['run_id']
            write(ROOT / 'formal/active.json', dict(time=timestamp(), cell=cell))
            task = read(ROOT / 'tasks' / (cell['task_id'] + '.json'))
            initial = engine.reset(task, cell['run_id'] + '_initial')
            engine.decorate(task['contract'])
            initial = engine.save(cell['run_id'] + '_initial')
            if canonical(initial) != canonical(read(ROOT / 'preflight' / task['id'] / 'initial_state.json')):
                raise RuntimeError('Formal initial state differs from preflight: ' + cell['run_id'])
            result = run_cell(task, cell['group'], engine, client, config, folder, initial,
                              seed=cell['seed'], stage='formal')
            result.update(repeat=cell['repeat'], seed=cell['seed'], block=cell['block'])
            write(folder / 'result.json', result)
            results.append(result)
            write(ROOT / 'formal/progress.json', dict(completed=results, planned=48, ledger_totals=ledger.totals()))
            print('FORMAL', len(results), '/48', cell['run_id'], 'success', result['complete_success'],
                  'stop', result['stop_reason'], 'cost', round(result['stats']['cost_cny'], 6), flush=True)
            if result['transport_failure']:
                break
    finally:
        engine.restore(context)
        write(ROOT / 'formal/summary.json', dict(time=timestamp(), planned=48, completed=len(results),
            results=results, ledger_totals=ledger.totals(), original_context_restored=engine.context() == context,
            development_runs=0))


if __name__ == '__main__':
    with Lock(ROOT / 'unity_execution.lock'):
        main()
