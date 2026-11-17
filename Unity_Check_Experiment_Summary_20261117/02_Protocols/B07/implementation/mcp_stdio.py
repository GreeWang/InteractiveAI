"""JSON-RPC client for the actual official Unity MCP stdio executable."""
import json
import selectors
import subprocess
import threading
import time
from pathlib import Path


class MCP:
    def __init__(self,project,log_path,client_name='check-native-mcp',command=None):
        self.log_path=Path(log_path);self.log_path.parent.mkdir(parents=True,exist_ok=True)
        self.id=0;self.stderr=[]
        command=command or ['unity','mcp','--project-path',str(project),'--no-log-proxy']
        self.log('session_start',dict(executable=command[0],arguments=command[1:],client=client_name))
        self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        threading.Thread(target=self._stderr,daemon=True).start()
        self.selector=selectors.DefaultSelector();self.selector.register(self.process.stdout,selectors.EVENT_READ)
        self.initialized=self.request('initialize',dict(protocolVersion='2024-11-05',capabilities={},clientInfo=dict(name=client_name,version='1.0')))
        self.notify('notifications/initialized',{})

    def _stderr(self):
        for line in self.process.stderr:
            self.stderr.append(line.rstrip())

    def log(self,direction,payload):
        with self.log_path.open('a') as f:f.write(json.dumps(dict(time=time.time(),direction=direction,payload=payload),ensure_ascii=False)+'\n')

    def notify(self,method,params):
        message=dict(jsonrpc='2.0',method=method,params=params);self.log('sent',message)
        self.process.stdin.write(json.dumps(message)+'\n');self.process.stdin.flush()

    def request(self,method,params,timeout=60):
        self.id+=1;rid=self.id;message=dict(jsonrpc='2.0',id=rid,method=method,params=params);self.log('sent',message)
        self.process.stdin.write(json.dumps(message)+'\n');self.process.stdin.flush();until=time.monotonic()+timeout
        while time.monotonic()<until:
            if not self.selector.select(max(.01,until-time.monotonic())):break
            line=self.process.stdout.readline()
            if not line:raise RuntimeError('Official MCP exited: '+str(self.stderr[-5:]))
            try:response=json.loads(line)
            except ValueError:self.log('non_json_stdout',line);continue
            self.log('received',response)
            if response.get('id')!=rid:continue
            if 'error' in response:raise RuntimeError('MCP error: '+json.dumps(response['error']))
            return response['result']
        raise TimeoutError('MCP request timeout: '+method+' '+str(self.stderr[-3:]))

    def tools(self):
        out=[];params={}
        while True:
            r=self.request('tools/list',params);out+=r['tools']
            if not r.get('nextCursor'):return out
            params=dict(cursor=r['nextCursor'])

    def call(self,name,arguments):return self.request('tools/call',dict(name=name,arguments=arguments),timeout=90)

    def close(self):
        if self.process.poll() is None:
            try:self.process.stdin.close();self.process.wait(timeout=5)
            except (subprocess.TimeoutExpired,BrokenPipeError):
                self.process.terminate()
                try:self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.selector.close()
        for pipe in [self.process.stdin,self.process.stdout,self.process.stderr]:
            if pipe and not pipe.closed:pipe.close()


if __name__=='__main__':
    import sys
    p=Path(__file__).resolve().parent/'probe';p.mkdir(exist_ok=True)
    m=MCP(sys.argv[1],p/'official_protocol.ndjson')
    try:
        tools=m.tools();(p/'official_tools.json').write_text(json.dumps(tools,ensure_ascii=False,indent=2)+'\n')
        (p/'initialize.json').write_text(json.dumps(m.initialized,ensure_ascii=False,indent=2)+'\n')
        print('OFFICIAL MCP INITIALIZED',m.initialized.get('serverInfo'))
        print('TOOLS',len(tools),[t['name'] for t in tools]);print('SCHEMA BYTES',len(json.dumps(tools,ensure_ascii=False).encode()))
    finally:m.close()
