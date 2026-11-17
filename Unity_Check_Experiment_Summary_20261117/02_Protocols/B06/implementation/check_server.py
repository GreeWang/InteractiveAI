"""Study-control MCP server; G4 additionally exposes the read-only Check package."""
import json
import sys
from pathlib import Path
from common import read,write
from mcp_stdio import MCP
from observer import snapshot,protected_diff,geometry
from online_check import check,compare
from feedback import check_feedback

FINISH=dict(name='finish',description='Submit your final study report. This reports your own conclusion; it neither edits Unity nor verifies task success.',
    inputSchema=dict(type='object',properties={
        'status':dict(type='string',enum=['complete','partial','failed']),
        'summary':dict(type='string'),
        **{k:dict(type='array',items=dict(type='string')) for k in ['verified','unresolved','limitations']}},
        required=['status','summary','verified','unresolved','limitations'],additionalProperties=False))
CHECK=[dict(name='check_constraints',description='Read-only: check every immutable public scene requirement and protected state. Returns counts and full details of every failure, not a reference layout. Facing failures contain current absolute yaw and signed RELATIVE error: yaw_next=(current_yaw_deg+signed_error_deg)%360. Takes no arguments.',inputSchema=dict(type='object',properties={},additionalProperties=False)),
       dict(name='compare_state',description='Read-only: compare actual scene with the immutable initial snapshot, list all actual object-field and protected component changes and whether permitted. Does not edit or restore anything. Takes no arguments.',inputSchema=dict(type='object',properties={},additionalProperties=False))]


def validate_finish(a):
    if set(a)!=set(FINISH['inputSchema']['required']):raise ValueError('Use exactly status, summary, verified, unresolved, limitations')
    if a['status'] not in ['complete','partial','failed'] or not isinstance(a['summary'],str):raise ValueError('Invalid status or summary')
    for key in ['verified','unresolved','limitations']:
        if not isinstance(a[key],list) or any(not isinstance(x,str) for x in a[key]):raise ValueError(key+' must be a list of strings, for example ["one short statement"]')


def full_check(state,initial,contract):
    old=[o['id'] for o in initial['objects']];now=[o['id'] for o in state['objects']]
    structural=protected_diff(state,initial)
    if sorted(now)!=sorted(old) or len(set(now))!=len(now):
        return dict(passed=False,rules=[dict(rule_id='inventory',passed=False,measured=now,expected=old),
            dict(rule_id='permissions',passed=False,measured=structural,expected='Initial inventory and protected scene structure unchanged; geometry unavailable for missing entities')])
    result=check(geometry(state),geometry(initial),contract)
    row=next(r for r in result['rules'] if r['rule_id']=='permissions');row['measured']+=structural;row['passed']=row['passed'] and not structural
    result['passed']=all(r['passed'] for r in result['rules']);return result


def full_compare(state,initial,contract):
    r=compare(geometry(state),geometry(initial),contract);r['differences']+=protected_diff(state,initial);r['passed']=all(x['authorized'] for x in r['differences']);return r


def main(folder,group):
    folder=Path(folder);context=read(folder/'server_context.json');initial=read(folder/'initial_state.json');contract=context['contract'];seq=0;unity=None
    def handle(method,p):
        nonlocal unity,seq
        if method=='initialize':return dict(protocolVersion='2024-11-05',capabilities=dict(tools={}),serverInfo=dict(name='study-finish-and-check' if group=='G4' else 'study-finish',version='1.0'))
        if method=='tools/list':return dict(tools=[FINISH]+(CHECK if group=='G4' else []))
        if method=='ping':return {}
        if method!='tools/call':raise ValueError('Unsupported method')
        name=p['name'];a=p.get('arguments',{})
        if name=='finish':
            validate_finish(a);write(folder/'finish_submitted.json',a);result=dict(submitted=True)
        else:
            if group!='G4' or name not in ['check_constraints','compare_state']:raise ValueError('Tool unavailable')
            if a:raise ValueError('The public contract and initial snapshot cannot be overridden')
            if unity is None:unity=MCP(context['project'],folder/'check_internal_official_rpc.ndjson',client_name='Check-read-only')
            version=read(folder/'current_version.json')['state_version'];state=snapshot(unity,version)
            full=full_check(state,initial,contract) if name=='check_constraints' else full_compare(state,initial,contract)
            seq+=1;write(folder/f'check_full_{seq:02}.json',dict(tool=name,state=state,result=full))
            result=check_feedback(full) if name=='check_constraints' else full
            result.update(state_version=version,contract_version=contract['contract_version'])
        return dict(content=[dict(type='text',text=json.dumps(result,ensure_ascii=False,separators=(',',':')))])
    try:
        for line in sys.stdin:
            try:
                request=json.loads(line)
                if 'id' not in request:continue
                value=handle(request['method'],request.get('params',{}));response=dict(jsonrpc='2.0',id=request['id'],result=value)
            except Exception as e:
                response=dict(jsonrpc='2.0',id=request.get('id'),result=dict(isError=True,content=[dict(type='text',text=type(e).__name__+': '+str(e))]))
            sys.stdout.write(json.dumps(response,ensure_ascii=False)+'\n');sys.stdout.flush()
    finally:
        if unity:unity.close()


if __name__=='__main__':main(sys.argv[1],sys.argv[2])
