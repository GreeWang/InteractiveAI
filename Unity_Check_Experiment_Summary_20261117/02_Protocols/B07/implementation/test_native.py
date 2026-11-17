import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from common import ROOT,read,write
from mcp_stdio import MCP
from observer import snapshot,protected_diff,digest
from native_provider import functions
from check_server import FINISH,CHECK,validate_finish,full_check
from run_actor import BASE,final_grade,prompt_bound


class NativeInterfaceTests(unittest.TestCase):
    def test_entire_official_catalog_preserved(self):
        native=read(ROOT/'probe/clone_tools.json');defs=functions(native)
        self.assertEqual(len(native),160);self.assertEqual(len(defs),160)
        for tool,definition in zip(native,defs):
            self.assertEqual(definition['function'],dict(name=tool['name'],description=tool.get('description',''),parameters=tool['inputSchema']))
        names={t['name'] for t in native};self.assertNotIn('inspect_scene',names);self.assertNotIn('apply_edits',names)
        self.assertTrue({'eval','batch','set_transform','get_scene_hierarchy'}.issubset(names))
    def test_no_private_reference_in_public_tasks(self):
        for p in (ROOT/'tasks').glob('*.json'):
            t=read(p);self.assertEqual(set(t),{'id','contract'});self.assertNotIn('witness',t['contract'])
    def test_finish_schema_is_shared_and_type_errors_remain_errors(self):
        good=dict(status='complete',summary='Actor claim, not a score',verified=[],unresolved=[],limitations=[])
        validate_finish(good)
        with self.assertRaises(ValueError):validate_finish(dict(good,verified=[{'not':'a string'}]))
        self.assertIn('response_output_cap',BASE)
    def test_schema_cost_is_in_input_bound(self):
        tools=functions(read(ROOT/'probe/clone_tools.json'));messages=[dict(role='user',content='Test')]
        self.assertGreater(prompt_bound(messages,tools,None),100000)
        self.assertLess(prompt_bound(messages,tools,(1,25000)),30000)
    def test_missing_native_entity_fails_safely(self):
        initial=read(ROOT/'probe/initial_observer.json');state=copy.deepcopy(initial);state['objects']=state['objects'][1:]
        c=read(ROOT/'tasks/D05.json')['contract'];self.assertFalse(full_check(state,initial,c)['passed']);self.assertFalse(final_grade(state,initial,c)['success'])
    def test_new_components_detected(self):
        initial=read(ROOT/'probe/initial_observer.json');state=copy.deepcopy(initial);state['protected_state']['new/component']='unexpected'
        self.assertTrue(protected_diff(state,initial));self.assertTrue(final_grade(state,initial,read(ROOT/'tasks/D05.json')['contract'])['protection_violation'])


class RealMCPTests(unittest.TestCase):
    def test_actual_shared_finish_and_g4_only_check_servers(self):
        cfg=read(ROOT/'config.json');unity=MCP(cfg['project'],ROOT/'probe/unit_readonly_official_rpc.ndjson')
        try:
            unity.call('open_scene',dict(path=cfg['scene_assets']['D05']));initial=snapshot(unity)
            for group in ['G2','G4']:
                with tempfile.TemporaryDirectory(prefix='native-mcp-unit-') as tmp:
                    folder=Path(tmp);write(folder/'server_context.json',dict(project=cfg['project'],contract=read(ROOT/'tasks/D05.json')['contract']))
                    write(folder/'initial_state.json',initial);write(folder/'current_version.json',dict(state_version=0))
                    server=MCP(None,folder/'rpc.ndjson',command=[sys.executable,str(ROOT/'check_server.py'),str(folder),group])
                    try:
                        tools=server.tools();self.assertEqual([t['name'] for t in tools],['finish']+(['check_constraints','compare_state'] if group=='G4' else []))
                        if group=='G2':self.assertTrue(server.call('check_constraints',{}).get('isError'))
                        else:
                            self.assertFalse(json.loads(server.call('check_constraints',{})['content'][0]['text'])['passed'])
                            self.assertTrue(json.loads(server.call('compare_state',{})['content'][0]['text'])['passed'])
                            self.assertTrue(server.call('check_constraints',dict(requirements=[])).get('isError'))
                        self.assertFalse(server.call('finish',dict(status='complete',summary='synthetic false claim',verified=[],unresolved=[],limitations=[])).get('isError',False))
                    finally:server.close()
            self.assertEqual(digest(snapshot(unity)),digest(initial))
        finally:unity.close()


if __name__=='__main__':unittest.main()
