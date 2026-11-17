"""Formal adapter, unchanged intervention and genuinely disjoint task fixtures."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from common import ROOT,read
from run_formal import make_schedule
from run_development import run_cell
from test_runtime import MemoryEngine,ScriptedClient,FINISH


class FormalTests(unittest.TestCase):
    def test_schedule_and_counterbalance(self):
        ids=read(ROOT/'task_manifest.json')['formal'];cells=make_schedule(ids,2026111603)
        self.assertEqual(cells,make_schedule(ids,2026111603));self.assertEqual(len(cells),48)
        self.assertEqual(len({c['run_id'] for c in cells}),48)
        self.assertEqual(sum(cells[i]['group']=='G2' for i in range(0,48,2)),12)
        for tid in ids:
            for repeat in [1,2]:
                pair=[c for c in cells if c['task_id']==tid and c['repeat']==repeat]
                self.assertEqual({c['group'] for c in pair},{'G2','G4'});self.assertEqual({c['seed'] for c in pair},{repeat})
    def test_v3_agent_budget_feedback_and_common_settings_unchanged(self):
        src=ROOT.parent/'check_v3_development'
        for name in ['common.py','provider.py','online_check.py','offline_score.py','feedback.py','budgeting.py','run_development.py']:
            self.assertEqual((ROOT/name).read_bytes(),(src/name).read_bytes())
        for p in (ROOT/'skills').glob('*.md'):self.assertEqual(p.read_bytes(),(src/'skills'/p.name).read_bytes())
        self.assertEqual((ROOT/'engine.py').read_text(),(src/'engine.py').read_text().replace('check_v3d_','check_v3f_'))
        a,b=read(src/'config.json'),read(ROOT/'config.json')
        for key in ['model','temperature','enable_thinking','limits','finalization_reserve','pricing','base_url','tls_max_version']:self.assertEqual(a[key],b[key])
    def test_new_ids_and_new_geometry(self):
        old=[]
        for root in [ROOT.parent/'check_v2_formal',ROOT.parent/'check_v3_development']:
            old += [read(p) for p in (root/'tasks').glob('*.json')]
        ids={o['id'] for t in old for o in t['initial']['objects'] if o['id']!='Floor'}
        def geometry(t):return sorted(json.dumps({k:o[k] for k in ['position','rotation','scale']},sort_keys=True) for o in t['initial']['objects'])
        old_geometry=[geometry(t) for t in old];new=[read(p) for p in (ROOT/'tasks').glob('*.json')]
        self.assertEqual(len(new),12)
        for t in new:
            self.assertFalse(ids.intersection(o['id'] for o in t['initial']['objects'] if o['id']!='Floor'))
            self.assertNotIn(geometry(t),old_geometry)
        self.assertEqual(len(read(ROOT/'task_manifest.json')['families']),6)
    def test_seed_two_and_formal_stage_propagate(self):
        class Recorder(ScriptedClient):
            def chat(self,messages,stage,key,seed,*args,**kwargs):
                self.seen=(stage,seed);return super().chat(messages,stage,key,seed,*args,**kwargs)
        old=ROOT.parent/'check_v2_formal';task=read(old/'tasks/M01.json');initial=read(old/'preflight/M01/initial_state.json');actor=Recorder([FINISH])
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'synthetic';run_cell(task,'G2',MemoryEngine(initial),actor,read(ROOT/'config.json'),folder,initial,seed=2,stage='formal')
            self.assertEqual(actor.seen,('formal',2));self.assertEqual(read(folder/'request_01.json')['seed'],2)


if __name__=='__main__':unittest.main()
