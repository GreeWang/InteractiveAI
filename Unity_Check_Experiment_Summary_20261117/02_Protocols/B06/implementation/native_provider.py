"""Qwen native function calling with unchanged official MCP tool definitions."""
import json
import urllib.request
import urllib.error
from common import ROOT,write,timestamp
from provider import Client,UnknownOutcome


class NativeClient(Client):
    def chat_tools(self,messages,tools,stage,key,seed,max_output,timeout,prompt_bound,finish_only=False):
        body=dict(model=self.config['model'],messages=messages,tools=tools,temperature=self.config['temperature'],seed=seed,
            max_tokens=max_output,enable_thinking=False,parallel_tool_calls=False,
            tool_choice={'type':'function','function':{'name':'finish'}} if finish_only else 'auto')
        reservation=self.ledger.reserve(stage,key,prompt_bound,max_output)
        req=urllib.request.Request(self.config['base_url'].rstrip('/')+'/chat/completions',data=json.dumps(body,ensure_ascii=False).encode(),
            headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=timeout,context=self.ssl_context) as response:payload=json.load(response)
        except Exception as ex:
            detail=type(ex).__name__
            if isinstance(ex,urllib.error.HTTPError):detail+=' HTTP '+str(ex.code)+' '+ex.read(4000).decode(errors='replace')
            detail=detail.replace(self.key,'[REDACTED]');write(ROOT/'transport'/(reservation['request_id']+'_error.json'),dict(time=timestamp(),diagnostic=detail,request_id=reservation['request_id']))
            raise UnknownOutcome(detail) from None
        write(ROOT/'transport'/(reservation['request_id']+'_response.json'),payload)
        cost=self.ledger.complete(reservation,payload.get('usage',{}))
        return dict(payload=payload,cost_cny=cost,request_id=reservation['request_id'])


def functions(tools):
    return [dict(type='function',function=dict(name=t['name'],description=t.get('description',''),parameters=t['inputSchema'])) for t in tools]


if __name__=='__main__':
    from provider import Ledger,input_bound
    from common import read
    cfg=read(ROOT/'config.json');tools=functions(read(ROOT/'probe/official_tools.json'))
    messages=[dict(role='system',content='You are testing native function-calling compatibility. Call get_scene_hierarchy with an empty arguments object. Do not call another tool or change anything.'),dict(role='user',content='Inspect the scene hierarchy.')]
    bound=input_bound(messages)+len(json.dumps(tools).encode())+1024
    write(ROOT/'probe/function_request.json',dict(messages=messages,tools=tools,input_bound=bound,maximum_output=512))
    c=NativeClient(cfg,Ledger(ROOT/'cost_ledger.ndjson',cfg));r=c.chat_tools(messages,tools,'pilot','native_160_tool_compatibility',1,512,120,bound)
    write(ROOT/'probe/function_response.json',r['payload']);print('Native function calling accepted',len(tools),'tools; cost',r['cost_cny']);print(r['payload']['choices'][0]['message'])
