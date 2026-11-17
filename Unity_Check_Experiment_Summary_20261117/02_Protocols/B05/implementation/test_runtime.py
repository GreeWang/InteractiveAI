"""In-memory isolation and contract checks; no Unity or network calls."""
import copy,json,tempfile,unittest
from pathlib import Path
from common import ROOT,read
from run_development import initial_messages,run_cell

FINISH={'tool':'finish','arguments':{'status':'partial','summary':'Synthetic unit test only','verified':[],'unresolved':['not edited'],'limitations':[]}}

class MemoryEngine:
    def __init__(self,state):self.state=copy.deepcopy(state)
    def inspect(self):return copy.deepcopy(self.state)
    def save(self,*args):return self.inspect()
    def render(self,*args,**kwargs):pass

class ScriptedClient:
    def __init__(self,actions):self.actions=iter(actions)
    def chat(self,*args,**kwargs):
        action=next(self.actions)
        return dict(request_id='synthetic-unit-test',cost_cny=0,payload={'model':'SYNTHETIC_UNIT_TEST','usage':{'prompt_tokens':1,'completion_tokens':1},'choices':[{'message':{'content':json.dumps(action)}}]})

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.task=read(ROOT.parent/'check_v2_formal/tasks/M01.json');self.initial=read(ROOT.parent/'check_v2_formal/preflight/M01/initial_state.json');self.cfg=read(ROOT/'config.json')
    def run_script(self,group,actions):
        with tempfile.TemporaryDirectory(prefix='check-v2-isolated-unit-') as tmp:
            folder=Path(tmp)/'unit_mock'
            result=run_cell(self.task,group,MemoryEngine(self.initial),ScriptedClient(actions),self.cfg,folder,self.initial)
            events=[json.loads(x) for x in (folder/'trace.ndjson').read_text().splitlines()]
        return result,events
    def test_g2_cannot_access_diagnostics(self):
        result,events=self.run_script('G2',[{'tool':'check_constraints','arguments':{}},FINISH])
        self.assertIn('unavailable',events[0]['observation']['message'])
        self.assertEqual(result['stats']['tools'],2);self.assertEqual(result['stats']['check_constraints'],0)
    def test_g4_cannot_override_contract_and_invalid_call_is_counted(self):
        result,events=self.run_script('G4',[{'tool':'check_constraints','arguments':{'requirements':[]}}, {'tool':'check_constraints','arguments':{}},FINISH])
        self.assertIn('immutable',events[0]['observation']['message'])
        self.assertFalse(events[1]['observation']['passed'])
        self.assertEqual(result['stats']['check_constraints'],2)
    def test_private_reference_and_grades_not_sent(self):
        for group,count in [('G2',1),('G4',2)]:
            messages,skills=initial_messages(self.task,group,self.initial,self.cfg);user=json.loads(messages[1]['content'])
            self.assertEqual(len(skills),count)
            self.assertNotIn('witness',user);self.assertNotIn('witness',user['public_contract'])
            self.assertEqual(set(user),{'task','public_contract','initial_state'})
            self.assertNotIn('check_constraints: {}',messages[0]['content']) if group=='G2' else self.assertIn('check_constraints: {}',messages[0]['content'])

if __name__=='__main__':unittest.main()
