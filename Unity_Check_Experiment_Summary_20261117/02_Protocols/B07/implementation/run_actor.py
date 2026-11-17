"""Same real official tools for both arms; G4 alone gets the Check MCP server tools."""
import copy
import json
import time
import sys
from common import ROOT,read,write,append,digest,timestamp
from mcp_stdio import MCP
from native_provider import functions,NativeClient
from observer import snapshot,geometry,digest as state_digest,protected_diff,decode
from offline_score import score

BASE='''You are editing the currently open Unity scene through the official Unity MCP tools supplied to you. Use their original names, schemas and results. You may independently inspect, calculate, validate and repair with native tools, including scene-only eval or batch operations.
Follow the public task contract. Only the listed root world position/yaw fields may change. All other initial scene objects, hierarchy, components, mesh geometry, materials and fields are protected. Keep Editor edit mode. Do not create/delete objects, alter scale/parents, edit scripts/packages/project settings/assets, launch OS processes, use network access or read experimental artifacts/reference layouts/other runs. Do not open other task scenes. The host saves results after you finish; do not save scene files yourself. The complete official tool catalog is available; task permission and resource limits still apply.
Use finish to submit your own report. It is a shared study-control tool, not an official Unity operation. Report lists contain STRINGS only. Do not treat a successful tool call as task success. You may report partial/failed with unresolved issues. The host does not correct your claims or complete the scene for you.
Limits per run: 16 model requests, 40 actor MCP calls, cumulative 512000 input and 16000 output tokens, 1200 monotonic seconds. Full tool schemas and repeated message history count as input every request. Native batch/eval internal operations count as one MCP call; no artificial scene-operation aliases or per-object write wrappers exist. Resource reminders are before the next request. response_output_cap is this response's output-token limit. A reserved final phase forces the finish function and allows only reporting/correction; keep the report concise and list a few short statements, not detailed per-object dumps.
'''
CHECK_GUIDE='''Additional Check package: check_constraints evaluates immutable public requirements and protected state; compare_state compares with the immutable initial snapshot. Both are read-only. After a native call changes the scene, use check_constraints then compare_state before another edit or claiming verified success. Check results identify the current state_version. After any new change, old diagnostics are stale. Use failed-rule measurements to repair only permitted fields; signed_error_deg is a relative yaw correction, never an absolute angle. Native scene operations, not Check, perform repairs. If the resource reminder switches to finish_only, report from existing evidence and list missing diagnostics instead of requesting more tools. Do not claim a geometric contradiction just because support and non-overlap tolerances differ.'''


def final_grade(state,initial,c):
    r=score(geometry(state),geometry(initial),c);extra=protected_diff(state,initial)
    r['checks'].append(dict(rule_id='native_protected_structure',passed=not extra,category='protection',measurement=dict(changes=extra)))
    r['success']=r['success'] and not extra;r['protection_violation']=r['protection_violation'] or bool(extra);return r


def prompt_bound(messages,tools,prefix):
    from provider import input_bound
    return input_bound(messages,prefix)+(len(json.dumps(tools,ensure_ascii=False,separators=(',',':')).encode())+1024 if prefix is None else 0)


def workflow(version,last,changed):
    if not changed:return dict(state_version=version,pending=[])
    c=last.get('check_constraints');d=last.get('compare_state');checked=bool(c and c['version']==version)
    compared=bool(d and d['version']==version and checked and d['turn']>c['turn'])
    return dict(state_version=version,pending=([] if checked else ['check_constraints'])+([] if compared else ['compare_state']))


def run_cell(cell,task,cfg,stage,folder,client):
    folder.mkdir(parents=True,exist_ok=False);c=task['contract'];cap=cfg['limits'];reserve=cfg['finalization_reserve'];group=cell['group']
    control=MCP(cfg['project'],folder/'host_official_rpc.ndjson',client_name='study-observer')
    actor=study=None;finish=None;stop='request_limit';version=0;last={};trace=[];mutations=[];finalization=[];prefix=None;final_only=False;transport=None
    stats=dict(requests=0,tools=0,official_tools=0,check_constraints=0,compare_state=0,input_tokens=0,output_tokens=0,cost_cny=0,changed_steps=0)
    try:
        opened=control.call('open_scene',dict(path=cfg['scene_assets'][task['id']],additive=False));assert not opened.get('isError'),opened
        initial=snapshot(control);assert state_digest(initial)==state_digest(read(ROOT/'audit/immutable_initial_states'/(task['id']+'.json'))),'Initial state differs from pre-model preflight';state=initial;write(folder/'initial_state.json',initial)
        write(folder/'server_context.json',dict(project=cfg['project'],contract=c));write(folder/'current_version.json',dict(state_version=0))
        actor=MCP(cfg['project'],folder/'actor_official_rpc.ndjson',client_name='scene-edit-agent')
        native=actor.tools();assert native==read(ROOT/'probe/clone_tools.json'),'Official catalog drift'
        study=MCP(None,folder/'study_rpc.ndjson',client_name='scene-study-client',command=[sys.executable,str(ROOT/'check_server.py'),str(folder),group]);extra=study.tools()
        tools=functions(native+extra);write(folder/'actual_tool_catalog.json',dict(official=native,study=extra,openai_functions=tools))
        system=BASE+'\nOfficial server instructions:\n'+str(actor.initialized.get('instructions',''))+('\n'+CHECK_GUIDE if group=='G4' else '')
        messages=[dict(role='system',content=system),dict(role='user',content=json.dumps(dict(task=c['request'],public_contract=c),ensure_ascii=False,separators=(',',':')))]
        write(folder/'initial_context.json',dict(messages=messages,official_server=actor.initialized,tools_sha256=digest(tools)))
        started=time.monotonic();wall=time.time()
        for turn in range(cap['requests']):
            elapsed=time.monotonic()-started
            if elapsed>=cap['seconds']:stop='time_limit';break
            b=dict(remaining_requests=cap['requests']-stats['requests'],remaining_tools=cap['tools']-stats['tools'],remaining_input_tokens=cap['input_tokens']-stats['input_tokens'],remaining_output_tokens=cap['output_tokens']-stats['output_tokens'],remaining_seconds=round(cap['seconds']-elapsed,3),state_version=version,finish_only=final_only,response_output_cap=2048)
            resource=dict(resource_budget=b)
            if group=='G4':resource['workflow_state']=workflow(version,last,bool(mutations))
            proposed=messages+[dict(role='user',content=json.dumps(resource))];bound=prompt_bound(proposed,tools,prefix)
            reasons=[];needed=max(reserve['input_tokens'],2*(bound+8192))
            if cap['requests']-stats['requests']<=2:reasons.append('request_reserve')
            if stats['input_tokens']+bound+needed>cap['input_tokens']:reasons.append('input_reserve')
            if cap['output_tokens']-stats['output_tokens']<reserve['output_tokens']+2048:reasons.append('output_reserve')
            if cap['seconds']-elapsed<reserve['seconds']+270:reasons.append('time_reserve')
            if final_only or reasons:
                if not final_only:finalization.append(dict(turn=turn+1,reasons=reasons,input_reserve=needed))
                final_only=True;b['finish_only']=True
            messages.append(dict(role='user',content=json.dumps(resource)));bound=prompt_bound(messages,tools,prefix)
            if stats['input_tokens']+bound>cap['input_tokens']:stop='input_budget_precheck';break
            remaining=cap['output_tokens']-stats['output_tokens']
            if remaining<=0:stop='output_budget';break
            write(folder/f'request_{turn+1:02}.json',dict(messages=messages,tools=tools,input_bound=bound,seed=cell['seed'],finish_only=final_only,max_output=min(2048,remaining)))
            try:
                stats['requests']+=1;response=client.chat_tools(messages,tools,stage,folder.name+'_request_'+str(turn+1),cell['seed'],min(2048,remaining),min(180,max(1,cap['seconds']-elapsed)),bound,final_only)
            except Exception as e:
                from provider import UnknownOutcome,BudgetStop
                if not isinstance(e,(UnknownOutcome,BudgetStop)):raise
                transport=type(e).__name__;stop=transport;write(folder/'transport_failure.json',dict(type=transport,message=str(e)));break
            p=response['payload'];write(folder/f'response_{turn+1:02}.json',p);usage=p['usage'];stats['input_tokens']+=usage['prompt_tokens'];stats['output_tokens']+=usage['completion_tokens'];stats['cost_cny']+=response['cost_cny'];prefix=(len(messages),usage['prompt_tokens'])
            msg=p['choices'][0]['message'];calls=msg.get('tool_calls') or [];forward={k:msg[k] for k in ['role','content'] if k in msg}
            if calls:forward['tool_calls']=[{k:t[k] for k in ['id','type','function']} for t in calls]
            messages.append(forward)
            if not calls:
                entry=dict(turn=turn+1,request_id=response['request_id'],tool=None,error='No function call',content=msg.get('content'));trace.append(entry);append(folder/'trace.ndjson',entry)
                messages.append(dict(role='user',content='Use the supplied native function tools; submit a report via finish, not plain text.'));continue
            for call in calls:
                stats['tools']+=1;name=call['function']['name'];raw_args=call['function']['arguments'];entry=dict(turn=turn+1,request_id=response['request_id'],tool_call_id=call['id'],tool=name,raw_arguments=raw_args,state_version_before=version)
                try:
                    args=json.loads(raw_args);entry['arguments']=args
                    if not isinstance(args,dict):raise ValueError('Tool arguments must be an object')
                    if stats['tools']>cap['tools']:raise ValueError('Actor tool budget exhausted')
                    if finish is not None:raise ValueError('Run already finished; no further tool executed')
                    if final_only and name!='finish':raise ValueError('Reporting phase permits only finish')
                    if name in [t['name'] for t in extra]:
                        result=study.call(name,args)
                        if name in ['check_constraints','compare_state']:
                            stats[name]+=1
                            if not result.get('isError'):
                                value=decode(result);last[name]=dict(version=value['state_version'],turn=turn+1,passed=value['passed'])
                        if name=='finish' and not result.get('isError') and decode(result).get('submitted'):finish=copy.deepcopy(args);stop='finish'
                    else:
                        stats['official_tools']+=1;result=actor.call(name,args)
                except Exception as e:result=dict(isError=True,content=[dict(type='text',text=type(e).__name__+': '+str(e))])
                entry['mcp_result']=result;new=snapshot(control,version)
                if state_digest(new)!=state_digest(state):
                    version+=1;new['state_version']=version;stats['changed_steps']+=1;mutations.append(dict(turn=turn+1,tool_index=stats['tools'],state=new));write(folder/f'after_change_{len(mutations):02}.json',new)
                entry['state_version_after']=version;entry['scene_changed']=state_digest(new)!=state_digest(state);state=new;write(folder/'current_version.json',dict(state_version=version))
                trace.append(entry);append(folder/'trace.ndjson',entry);messages.append(dict(role='tool',tool_call_id=call['id'],content=json.dumps(result,ensure_ascii=False,separators=(',',':'))))
            if finish is not None:break
        seconds=time.monotonic()-started;wall_seconds=time.time()-wall;final=snapshot(control,version);grade=final_grade(final,initial,c)
        write(folder/'final_state.json',final);write(folder/'finish.json',finish);write(folder/'offline_final_score.json',grade)
        grades=[final_grade(x['state'],initial,c) for x in mutations]
        for i,g in enumerate(grades):write(folder/f'offline_change_{i+1:02}.json',g)
        normal=finish is not None and stop=='finish' and seconds<=cap['seconds'] and stats['tools']<=cap['tools']
        coverage=all(all(any(e.get('tool')==t and not e.get('mcp_result',{}).get('isError') and e.get('state_version_before')==v['state']['state_version'] for e in trace) for t in ['check_constraints','compare_state']) for v in mutations) if group=='G4' else None
        r=dict(**cell,normal_finish=normal,state_success=grade['success'],complete_success=normal and grade['success'],stop_reason=stop,finish=finish,
            initial_edit_failed=bool(grades) and not grades[0]['success'],self_repaired=bool(grades) and not grades[0]['success'] and grade['success'],
            false_complete=bool(finish and finish['status']=='complete' and not grade['success']),process_protection_violation=any(g['protection_violation'] for g in grades),final_protection_violation=grade['protection_violation'],
            flow_adherence=coverage,stats=stats,seconds=seconds,wall_seconds=wall_seconds,finalization=finalization,transport_failure=transport,model_ids=sorted({read(p)['model'] for p in folder.glob('response_*.json')}))
        write(folder/'result.json',r);write(folder/'full_messages.json',messages)
        # Save outside the actor-visible task set, then remove the capture before the next actor.
        path='Assets/NativeCapture/'+folder.name+'.unity'
        save_code='var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene(); return UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene,'+json.dumps(path)+',true);'
        saved=control.call('eval',dict(code=save_code,timeout=30000));write(folder/'scene_save_response.json',saved)
        assert decode(saved).get('success') and decode(saved).get('result') is True,'Native scene copy failed: '+str(saved)
        import shutil
        from pathlib import Path
        asset=Path(cfg['project'])/path
        for suffix in ['', '.meta']:shutil.copy2(Path(str(asset)+suffix),folder/('final_scene.unity'+suffix))
        assert state_digest(snapshot(control,version))==state_digest(final),'Host scene copy changed final state'
        write(folder/'capture_provenance.json',dict(kind='actual_native_post_run_copy',method='official MCP eval: EditorSceneManager.SaveScene(saveAsCopy:true)',actor_already_finished=True,final_state_unchanged=True))
        control.call('open_scene',dict(path=cfg['scene_assets'][task['id']],additive=False))
        for suffix in ['', '.meta']:Path(str(asset)+suffix).unlink(missing_ok=True)
        return r
    finally:
        if study:study.close()
        if actor:actor.close()
        control.close()
