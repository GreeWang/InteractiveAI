"""Round2 changes: numeric feedback semantics, reminders, and unchanged controls."""
import copy,json,math,unittest
from common import ROOT,read
from online_check import check
from run_development import initial_messages,workflow_state
from test_runtime import MemoryEngine,ScriptedClient,FINISH

OLD=ROOT.parent/'check_v2_execution'

class FeedbackTests(unittest.TestCase):
    def facing(self,current,desired):
        q=[0,math.sin(math.radians(current/2)),0,math.cos(math.radians(current/2))]
        o=dict(id='Chair',position=[0,.5,0],rotation=[0,current,0],quaternion=q,scale=[.5,1,.5],name='Chair',kind='chair',category='',parent='',bounds_min=[-.25,0,-.25],bounds_max=[.25,1,.25])
        s={'objects':[o]};c=dict(id='UNIT',scene='D',allowed={'Chair':['yaw']},regions=[],inside=[],support=[],grounded=[],facing=[['Chair','P']],relative=[],distance=[],keepout=[],markers={'P':[math.sin(math.radians(desired)),0,math.cos(math.radians(desired))]})
        return check(s,s,c)['rules'][1]['measured']
    def test_signed_correction_all_quadrants_and_wrap(self):
        for current,target,expected in [(0,90,90),(0,270,-90),(350,10,20),(10,350,-20),(90,0,-90),(270,0,90),(45,45,0)]:
            with self.subTest(current=current,target=target):
                m=self.facing(current,target)
                self.assertAlmostEqual(m['signed_error_deg'],expected,places=6)
                corrected=(m['current_yaw_deg']+m['signed_error_deg'])%360
                self.assertLess(abs((corrected-target+180)%360-180),1e-6)
    def test_failed_check_still_requires_diff_and_new_edit_resets(self):
        self.assertEqual(workflow_state(2,True,{})['pending'],['check_constraints','compare_state'])
        check_at_2={'version':2,'turn':3,'passed':False}
        self.assertEqual(workflow_state(2,True,{'check_constraints':check_at_2})['next'],'compare_state')
        latest={'check_constraints':check_at_2,'compare_state':{'version':2,'turn':4,'passed':True}}
        self.assertEqual(workflow_state(2,True,latest)['pending'],[])
        self.assertFalse(workflow_state(2,True,latest)['goals_passed'])
        self.assertEqual(workflow_state(3,True,latest)['pending'],['check_constraints','compare_state'])
        latest['compare_state']['turn']=2
        self.assertEqual(workflow_state(2,True,latest)['next'],'compare_state')
    def test_g2_initial_context_is_identical_to_round1(self):
        for tid in ['D01','D02','D03','D04']:
            f=OLD/'development'/(tid+'_G2_r1');initial=read(f/'initial_state.json');task=read(ROOT/'tasks'/(tid+'.json'))
            messages,skills=initial_messages(task,'G2',initial,read(ROOT/'config.json'))
            previous=read(f/'initial_context.json')
            self.assertEqual(messages,previous['messages']);self.assertEqual(skills,previous['loaded_skills'])
        a=read(OLD/'config.json');b=read(ROOT/'config.json')
        for k in ['model','temperature','enable_thinking','limits','base_url','pricing']:self.assertEqual(a[k],b[k])

class ReminderDoesNotEnforceTests(unittest.TestCase):
    def setUp(self):
        self.task=read(ROOT/'tasks/M01.json');self.initial=read(ROOT/'preflight/M01/initial_state.json');self.cfg=read(ROOT/'config.json')
    def test_missing_diagnostics_do_not_block_finish_or_create_evidence(self):
        from run_development import run_cell
        from pathlib import Path
        import tempfile
        class EditableMemoryEngine(MemoryEngine):
            def apply(self,edits):
                self.state['state_version']+=1
                return dict(operations=[dict(id=e['id'],ok=True) for e in edits],state_version=self.state['state_version'])
        with tempfile.TemporaryDirectory(prefix='round2-no-enforcement-') as tmp:
            actions=[{'tool':'apply_edits','arguments':{'edits':[{'id':'T','yaw':0}]}},{'tool':'finish','arguments':{**FINISH['arguments'],'status':'complete'}}]
            result=run_cell(self.task,'G4',EditableMemoryEngine(self.initial),ScriptedClient(actions),self.cfg,Path(tmp)/'synthetic',self.initial)
            self.assertTrue(result['normal_finish']);self.assertTrue(result['false_complete']);self.assertFalse(result['flow_adherence'])
            self.assertEqual(result['stats']['check_constraints'],0);self.assertEqual(result['stats']['compare_state'],0)

if __name__=='__main__':unittest.main()
