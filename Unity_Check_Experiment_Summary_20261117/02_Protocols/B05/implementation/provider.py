"""One serial, durable cost ledger. Unknown requests remain fully reserved."""
from __future__ import annotations
import fcntl
import json
import math
import os
import ssl
import urllib.request
import urllib.error
import uuid
from pathlib import Path
from common import ROOT, read, write, append, timestamp

class BudgetStop(Exception):pass
class UnknownOutcome(Exception):pass

class Lock:
    def __init__(self,path):self.path=Path(path)
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True);self.file=self.path.open("a+")
        try:fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:self.file.close();raise RuntimeError("Another experiment owns this lock")
        return self
    def __exit__(self,*args):fcntl.flock(self.file,fcntl.LOCK_UN);self.file.close()

def ledger_entries(path):
    latest={}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            event=json.loads(line);latest[event["request_id"]]=event
    return list(latest.values())

def unapproved_unknown_requests(path,stage):
    exception_file=ROOT/"audit/unknown_request_exceptions.json"
    exceptions=read(exception_file).get("exceptions",[]) if exception_file.exists() else []
    def authorized(entry):
        return entry["status"]=="reserved_unknown" and any(
            e.get("request_id")==entry["request_id"] and e.get("scope")==stage and e.get("user_authorization")
            and e.get("preserve_full_reservation") is True and type(e.get("reserved_cny")) in (int,float)
            and math.isclose(e["reserved_cny"],entry["charged_upper_cny"],rel_tol=0,abs_tol=1e-9)
            for e in exceptions)
    return [e for e in ledger_entries(path) if e["status"]!="completed" and not authorized(e)]

class Ledger:
    def __init__(self,path,config):self.path=Path(path).resolve();self.config=config
    def totals(self):
        entries=ledger_entries(self.path)
        return {"total":sum(e["charged_upper_cny"] for e in entries),**{s:sum(e["charged_upper_cny"] for e in entries if e["stage"]==s) for s in ["pilot","formal","reserve"]}}
    def global_totals(self):
        entries={}
        for path in self.config.get('global_budget',{}).get('ledger_sources',[])+[str(self.path)]:
            for e in ledger_entries(path):
                old=entries.get(e['request_id'])
                if old is None or e['charged_upper_cny']>old['charged_upper_cny']:entries[e['request_id']]=e
        return dict(total=sum(e['charged_upper_cny'] for e in entries.values()),requests=len(entries),
                    unknown_requests=sum(e['status']!='completed' for e in entries.values()))
    def reserve(self,stage,key,input_bound,max_output):
        rates=self.config["pricing"]
        amount=(input_bound*rates["input_cny_per_million"]+max_output*rates["output_cny_per_million"])/1e6
        global_budget=self.config.get('global_budget',{})
        with Lock(global_budget.get('lock_file',str(self.path)+'.global.lock')),Lock(str(self.path)+".lock"):
            if unapproved_unknown_requests(self.path,stage):raise UnknownOutcome("Unreconciled previous API request; stop before any further spending")
            spent=self.totals();limits=self.config["budget_cny"]
            if self.global_totals()['total']+amount>global_budget.get('limit_cny',float('inf'))+1e-9:raise BudgetStop('Aggregate local API budget exhausted')
            if spent["total"]+amount>limits["total"]+1e-9 or spent[stage]+amount>limits[stage]+1e-9:raise BudgetStop("Stage or total budget exhausted")
            if spent['total']+amount-self.config.get('budget_starting_total_cny',0)>self.config.get('current_batch_max_cny',float('inf'))+1e-9:raise BudgetStop('Current pilot batch budget exhausted')
            e=dict(request_id=uuid.uuid4().hex,time=timestamp(),stage=stage,key=key,status="reserved_unknown",charged_upper_cny=amount,input_bound=input_bound,output_bound=max_output)
            append(self.path,e);return e
    def complete(self,reservation,usage):
        try:
            i=usage["prompt_tokens"];o=usage["completion_tokens"]
            if type(i)!=int or type(o)!=int or min(i,o)<0:raise ValueError()
        except (KeyError,ValueError,TypeError):raise UnknownOutcome("Response missing trustworthy token usage")
        rates=self.config["pricing"];cost=(i*rates["input_cny_per_million"]+o*rates["output_cny_per_million"])/1e6
        e={**reservation,"status":"completed","charged_upper_cny":cost,"usage":usage,"finished":timestamp()}
        append(self.path,e)
        if i>reservation["input_bound"] or o>reservation["output_bound"]:raise UnknownOutcome("Provider exceeded reserved token bound; stop and audit")
        return cost

def credentials(path):
    values={}
    for line in Path(path).read_text().splitlines():
        line=line.strip()
        if line and not line.startswith("#") and "=" in line:
            k,v=line.split("=",1);values[k.strip()]=v.strip().strip("'\"")
    # Explicit DashScope key is preferred; never print or persist this mapping.
    key=os.environ.get("DASHSCOPE_API_KEY") or values.get("DASHSCOPE_API_KEY") or os.environ.get("LLM_API_KEY") or values.get("LLM_API_KEY")
    if not key:raise RuntimeError("DashScope credential unavailable")
    return key

def input_bound(messages,known_prefix=None):
    # Reuse measured prompt-token count for the unchanged prefix. Only appended
    # messages need the conservative UTF-8 bound and chat-envelope safety margin.
    count,tokens=known_prefix or (0,0)
    tail=messages[count:]
    return tokens+len(json.dumps(tail,ensure_ascii=False,separators=(",",":")).encode())+512+32*len(tail)

class Client:
    def __init__(self,config,ledger):
        self.config=config;self.ledger=ledger;self.key=credentials(config["credential_file"])
        self.ssl_context=ssl.create_default_context()
        if config.get("tls_max_version")=="TLSv1_2":self.ssl_context.maximum_version=ssl.TLSVersion.TLSv1_2
    def chat(self,messages,stage,key,seed,remaining_output,timeout,prompt_bound=None):
        max_output=min(2048,remaining_output)
        body=dict(model=self.config["model"],messages=messages,temperature=self.config["temperature"],seed=seed,max_tokens=max_output,enable_thinking=self.config["enable_thinking"],response_format={"type":"json_object"})
        reservation=self.ledger.reserve(stage,key,prompt_bound if prompt_bound is not None else input_bound(messages),max_output)
        request=urllib.request.Request(self.config["base_url"].rstrip("/")+"/chat/completions",data=json.dumps(body,ensure_ascii=False).encode(),headers={"Authorization":"Bearer "+self.key,"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(request,timeout=timeout,context=self.ssl_context) as response:payload=json.load(response)
        except Exception as ex:
            # HTTP/transport outcomes are not retried: billing/non-execution is not known.
            reason=getattr(ex,"reason",None)
            detail=type(ex).__name__+(" / "+type(reason).__name__+" / "+str(reason) if reason is not None else "")
            if isinstance(ex,urllib.error.HTTPError):
                body_text=ex.read(4000).decode('utf-8',errors='replace').replace(self.key,'[REDACTED]')
                detail+=' / HTTP '+str(ex.code)+' / '+body_text
            # Explicitly redact the credential even in unusual transport exception text.
            detail=detail.replace(self.key,"[REDACTED]")
            write(ROOT/'transport'/(reservation['request_id']+'_error.json'),dict(time=timestamp(),diagnostic=detail,request_id=reservation['request_id']))
            raise UnknownOutcome("API request outcome unknown: "+detail) from None
        usage=payload.get("usage",{})
        write(ROOT/'transport'/(reservation['request_id']+'_response.json'),payload)
        cost=self.ledger.complete(reservation,usage)
        # Do not expose headers/credentials; retain standard response, usage, model and ID.
        return dict(payload=payload,cost_cny=cost,request_id=reservation["request_id"])
