"""Focused tests for the formal-only scheduling and seed/stage adaptation."""
import json
import tempfile
import unittest
from pathlib import Path
from common import ROOT, read
from run_development import run_cell
from run_formal import make_schedule
from test_runtime import MemoryEngine, ScriptedClient, FINISH


class FormalTests(unittest.TestCase):
    def test_schedule_exact_cells_and_counterbalance(self):
        tasks = read(ROOT / 'task_manifest.json')['formal']
        cells = make_schedule(tasks, 20261116)
        self.assertEqual(cells, make_schedule(tasks, 20261116))
        self.assertEqual(len(cells), 48)
        self.assertEqual(len({c['run_id'] for c in cells}), 48)
        self.assertEqual(sum(cells[i]['group'] == 'G2' for i in range(0, 48, 2)), 12)
        for tid in tasks:
            for repeat in [1, 2]:
                pair = [c for c in cells if c['task_id'] == tid and c['repeat'] == repeat]
                self.assertEqual({c['group'] for c in pair}, {'G2', 'G4'})
                self.assertEqual({c['seed'] for c in pair}, {repeat})

    def test_seed_and_stage_reach_client_and_saved_request(self):
        class Recorder(ScriptedClient):
            def chat(self, messages, stage, key, seed, *args, **kwargs):
                self.observed = (stage, seed)
                return super().chat(messages, stage, key, seed, *args, **kwargs)
        task = read(ROOT / 'tasks/M01.json')
        initial = read(ROOT / 'preflight/M01/initial_state.json')
        client = Recorder([FINISH])
        with tempfile.TemporaryDirectory(prefix='formal-seed-test-') as tmp:
            folder = Path(tmp) / 'synthetic'
            run_cell(task, 'G2', MemoryEngine(initial), client, read(ROOT / 'config.json'), folder, initial, seed=2, stage='formal')
            self.assertEqual(client.observed, ('formal', 2))
            self.assertEqual(read(folder / 'request_01.json')['seed'], 2)

    def test_agent_loop_only_seed_stage_parameters_changed(self):
        old = (ROOT.parent / 'check_v2_round2/run_development.py').read_text()
        expected = old.replace('def run_cell(task,group,engine,client,config,folder,initial):',
            "def run_cell(task,group,engine,client,config,folder,initial,seed=1,stage='pilot'):")
        expected = expected.replace("seed=1,model=config['model']", "seed=seed,model=config['model']")
        expected = expected.replace("client.chat(messages,'pilot',folder.name+'_request_'+str(turn+1),1,",
            "client.chat(messages,stage,folder.name+'_request_'+str(turn+1),seed,")
        self.assertEqual((ROOT / 'run_development.py').read_text(), expected)


if __name__ == '__main__':
    unittest.main()
