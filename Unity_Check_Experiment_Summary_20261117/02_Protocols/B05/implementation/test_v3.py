"""Behavioral regression tests; synthetic actors never count as development runs."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from common import ROOT, read
from budgeting import report_phase
from feedback import check_feedback
from provider import Ledger, BudgetStop
from run_development import run_cell
from test_runtime import MemoryEngine, ScriptedClient, FINISH


class FeedbackTests(unittest.TestCase):
    def test_full_failure_measurements_and_permissions_survive(self):
        rows=[dict(rule_id='pass',passed=True,measured='large',expected='large'),
            dict(rule_id='permissions',passed=False,measured=[dict(object='Fixed',field='position',before=[0,0,0],after=[1,0,0],authorized=False)],expected={}),
            dict(rule_id='facing:Seat',passed=False,measured=dict(current_yaw_deg=350,signed_error_deg=20,target_point=[1,0,1]),expected=dict(yaw_update_rule='relative'))]
        full=dict(passed=False,rules=rows);before=copy.deepcopy(full);lean=check_feedback(full)
        self.assertEqual(full,before);self.assertEqual(lean['checked_rule_count'],3);self.assertEqual(lean['passed_rule_count'],1)
        self.assertEqual([r['rule_id'] for r in lean['failures']],['permissions','facing:Seat'])
        self.assertEqual(lean['failures'][0]['measured'],rows[1]['measured'])
        self.assertEqual(lean['failures'][1]['measured']['signed_error_deg'],20)
    def test_all_pass_still_records_full_rule_count(self):
        self.assertEqual(check_feedback(dict(passed=True,rules=[dict(rule_id=str(i),passed=True) for i in range(100)])),dict(passed=True,checked_rule_count=100,passed_rule_count=100,failed_rule_count=0,failures=[]))
    def test_predicates_and_independent_score_unchanged(self):
        for name in ['online_check.py','offline_score.py']:
            self.assertEqual((ROOT/name).read_bytes(),(ROOT.parent/'check_v2_formal'/name).read_bytes())


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.cfg=read(ROOT/'config.json');self.caps=self.cfg['limits'];self.reserve=self.cfg['finalization_reserve']
        self.stats=dict(requests=0,tools=0,input_tokens=0,output_tokens=0)
    def test_reserve_prevents_consuming_last_output_and_time(self):
        self.assertFalse(report_phase(self.stats,self.caps,self.reserve,0,10000)[0])
        self.stats['output_tokens']=9000
        self.assertIn('output_reserve',report_phase(self.stats,self.caps,self.reserve,0,10000)[1])
        self.stats['output_tokens']=0
        self.assertIn('time_reserve',report_phase(self.stats,self.caps,self.reserve,1000,10000)[1])
    def test_token_request_and_tool_limits_enter_report_phase(self):
        self.stats['input_tokens']=60000
        self.assertIn('input_reserve',report_phase(self.stats,self.caps,self.reserve,0,12000)[1])
        self.stats['input_tokens']=0;self.stats['requests']=14
        self.assertIn('request_reserve',report_phase(self.stats,self.caps,self.reserve,0,10000)[1])
        self.stats['requests']=0;self.stats['tools']=38
        self.assertIn('tool_reserve',report_phase(self.stats,self.caps,self.reserve,0,10000)[1])
        self.stats['tools']=0
        self.assertTrue(report_phase(self.stats,self.caps,self.reserve,0,10000,True)[0])
    def test_global_budget_deduplicates_and_retains_unknowns(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);events=[dict(request_id='known',status='completed',charged_upper_cny=.2),dict(request_id='unknown',status='reserved_unknown',charged_upper_cny=.3)]
            for name in ['a','b']:(p/name).write_text(''.join(json.dumps(e)+'\n' for e in events))
            cfg=copy.deepcopy(self.cfg);cfg['global_budget']=dict(limit_cny=.5,ledger_sources=[str(p/'a'),str(p/'b')],lock_file=str(p/'global.lock'))
            ledger=Ledger(p/'new.ndjson',cfg)
            self.assertEqual(ledger.global_totals(),dict(total=.5,requests=2,unknown_requests=1))
            with self.assertRaises(BudgetStop):ledger.reserve('pilot','synthetic',100,100)
            self.assertFalse((p/'new.ndjson').exists())


class RuntimeReserveTests(unittest.TestCase):
    def setUp(self):
        old=ROOT.parent/'check_v2_formal'
        self.task=read(old/'tasks/M01.json');self.initial=read(old/'preflight/M01/initial_state.json');self.cfg=read(ROOT/'config.json')
    def test_both_groups_receive_tokens_time_and_report_before_exhaustion(self):
        class ResourceActor:
            def __init__(self):self.budgets=[];self.outputs=[]
            def chat(self,messages,stage,key,seed,remaining_output,timeout,**kwargs):
                b=json.loads(messages[-1]['content'])['resource_budget'];self.budgets.append(b);self.outputs.append(remaining_output)
                action=FINISH if b['finish_only'] else dict(tool='inspect_scene',arguments={})
                return dict(request_id='synthetic',cost_cny=0,payload=dict(model='SYNTHETIC',usage=dict(prompt_tokens=12000,completion_tokens=20),choices=[dict(message=dict(content=json.dumps(action)))]))
        for group in ['G2','G4']:
            actor=ResourceActor()
            with tempfile.TemporaryDirectory() as tmp:
                r=run_cell(self.task,group,MemoryEngine(self.initial),actor,self.cfg,Path(tmp)/'mock',self.initial)
            self.assertTrue(r['normal_finish']);self.assertFalse(r['complete_success']);self.assertTrue(r['finalization'])
            self.assertLess(r['stats']['requests'],14);self.assertLessEqual(r['stats']['input_tokens'],96000)
            self.assertTrue(actor.budgets[-1]['finish_only']);self.assertEqual(actor.outputs[-1],750)
            for b in actor.budgets:
                self.assertIn('remaining_input_tokens',b);self.assertIn('remaining_output_tokens',b);self.assertGreater(b['remaining_seconds'],0)
    def test_two_report_opportunities_allow_format_correction(self):
        cfg=copy.deepcopy(self.cfg);cfg['limits']['requests']=2
        actor=ScriptedClient([dict(tool='finish',arguments=dict(status='partial')),FINISH])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'mock';r=run_cell(self.task,'G2',MemoryEngine(self.initial),actor,cfg,p,self.initial)
            entries=[json.loads(x) for x in (p/'trace.ndjson').read_text().splitlines()]
        self.assertTrue(r['normal_finish']);self.assertIn('error',entries[0]['observation']);self.assertEqual(r['stats']['requests'],2)
    def test_no_automatic_report_or_scene_change(self):
        cfg=copy.deepcopy(self.cfg);cfg['limits']['requests']=2
        actor=ScriptedClient([dict(tool='apply_edits',arguments=dict(edits=[dict(id='T',yaw=90)])),dict(tool='inspect_scene',arguments={})])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'mock';r=run_cell(self.task,'G4',MemoryEngine(self.initial),actor,cfg,p,self.initial)
            self.assertEqual(read(p/'final_state.json'),self.initial)
        self.assertIsNone(r['finish']);self.assertFalse(r['normal_finish']);self.assertEqual(r['stats']['edit_batches'],0)
    def test_finish_is_not_rejected_using_private_score(self):
        action=dict(tool='finish',arguments={**FINISH['arguments'],'status':'complete'})
        with tempfile.TemporaryDirectory() as tmp:
            r=run_cell(self.task,'G4',MemoryEngine(self.initial),ScriptedClient([action]),self.cfg,Path(tmp)/'mock',self.initial)
        self.assertTrue(r['normal_finish']);self.assertTrue(r['false_complete'])
        self.assertEqual(r['stats']['check_constraints'],0);self.assertEqual(r['stats']['compare_state'],0)


if __name__=='__main__':unittest.main()
