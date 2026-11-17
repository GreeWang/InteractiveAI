"""Research-only Unity transport plus data-only, condition-independent writes."""
import base64
import json
import math
import subprocess
import time
from pathlib import Path
from common import ROOT,read,write,digest

class Engine:
    def __init__(self):self.config=read(ROOT/'config.json');self.version=0
    def evaluate(self,code):
        p=subprocess.run(['unity','command','--project-path',self.config['project'],'--format','json','--result-only','eval','--','--code',code],capture_output=True,text=True,timeout=45)
        try:r=json.loads(p.stdout)
        except ValueError:raise RuntimeError('Invalid Unity response: '+p.stdout[:400])
        if p.returncode or not r.get('success'):raise RuntimeError(str(r)[:1200])
        return r['result']
    def call(self,request):
        code='return P2SCV1Bridge.Dispatch('+json.dumps(base64.b64encode(json.dumps(request,ensure_ascii=False).encode()).decode())+');'
        r=json.loads(self.evaluate(code))
        if not r.get('ok'):raise RuntimeError(r.get('error','Unity bridge failed'))
        return r
    def inspect(self):
        s=self.call({'op':'inspect'})['state'];s['state_version']=self.version;return s
    def reset(self,task,key):
        path='Assets/P2SCV1/Scenes/check_v2f_'+key+'.unity'
        r=self.call(dict(op='reset',state=task['initial'],scene=path));self.version=0
        s=r['state'];s['state_version']=0;return s
    def save(self,key):
        s=self.call(dict(op='save_reload',scene='Assets/P2SCV1/Scenes/check_v2f_'+key+'.unity'))['state'];s['state_version']=self.version;return s
    def apply(self,edits):
        if not isinstance(edits,list) or not edits or len(edits)>100:raise ValueError('Provide 1–100 edits')
        ids={x['id'] for x in self.inspect()['objects']};clean=[]
        for e in edits:
            if not isinstance(e,dict) or set(e)-{'id','position','yaw'} or 'id' not in e or not set(e)&{'position','yaw'}:raise ValueError('Each edit needs id and position and/or yaw only')
            if e['id'] not in ids:raise ValueError('Unknown object id')
            out=dict(op='set',id=e['id'])
            if 'position' in e:
                a=e['position']
                if not isinstance(a,list) or len(a)!=3 or not all(type(v) in [int,float] and math.isfinite(v) for v in a):raise ValueError('Invalid position')
                if not (-7<=a[0]<=7 and -1<=a[1]<=8 and -6<=a[2]<=6):raise ValueError('Position outside common coordinate execution range')
                out['position']=a
            if 'yaw' in e:
                v=e['yaw']
                if type(v) not in [int,float] or not math.isfinite(v):raise ValueError('Invalid yaw')
                out['rotation']=[0,v%360,0]
            clean.append(out)
        r=self.call(dict(op='apply',edits=clean))
        self.version+=sum(bool(x['ok']) for x in r['operations'])
        # NO task-level permission or target correctness filtering here.
        return dict(operations=r['operations'],state_version=self.version)
    def context(self):
        s=self.evaluate('return Newtonsoft.Json.JsonConvert.SerializeObject(new {active=UnityEngine.SceneManagement.SceneManager.GetActiveScene().path,dirty=UnityEngine.SceneManagement.SceneManager.GetActiveScene().isDirty,count=UnityEngine.SceneManagement.SceneManager.sceneCount});')
        return json.loads(s)
    def restore(self,context):
        if context.get('active'):
            self.evaluate('UnityEditor.SceneManagement.EditorSceneManager.OpenScene('+json.dumps(context['active'])+');return true;')
    def decorate(self,contract):
        encoded=base64.b64encode(json.dumps(dict(regions=contract['regions'],keepout=contract['keepout'],markers=contract.get('markers',{}))).encode()).decode()
        code='''var cfg=Newtonsoft.Json.Linq.JObject.Parse(System.Text.Encoding.UTF8.GetString(System.Convert.FromBase64String(DATA)));
        var root=new UnityEngine.GameObject("Public region markers");
        var mat=new UnityEngine.Material(UnityEngine.Shader.Find("Universal Render Pipeline/Unlit")??UnityEngine.Shader.Find("Unlit/Color"));
        System.Action<string,UnityEngine.Vector3,UnityEngine.Vector3,UnityEngine.Color> line=(name,a,b,color)=>{var g=new UnityEngine.GameObject(name);g.transform.SetParent(root.transform);var l=g.AddComponent<UnityEngine.LineRenderer>();l.sharedMaterial=mat;l.positionCount=2;l.SetPosition(0,a);l.SetPosition(1,b);l.startWidth=.025f;l.endWidth=.025f;l.startColor=color;l.endColor=color;};
        foreach(var collection in new[]{"regions","keepout"}) foreach(var r in cfg[collection]) {float x0=(float)r["min"][0],x1=(float)r["max"][0],z0=(float)r["min"][2],z1=(float)r["max"][2],y=System.Math.Max(.02f,(float)r["min"][1]+.015f);var col=collection=="regions"?UnityEngine.Color.green:UnityEngine.Color.red;var pts=new[]{new UnityEngine.Vector3(x0,y,z0),new UnityEngine.Vector3(x1,y,z0),new UnityEngine.Vector3(x1,y,z1),new UnityEngine.Vector3(x0,y,z1)};for(int j=0;j<4;j++)line("Public zone edge",pts[j],pts[(j+1)%4],col);}
        foreach(var marker in (Newtonsoft.Json.Linq.JObject)cfg["markers"]){var a=(Newtonsoft.Json.Linq.JArray)marker.Value;float x=(float)a[0],z=(float)a[2];line(marker.Key,new UnityEngine.Vector3(x-.15f,.03f,z),new UnityEngine.Vector3(x+.15f,.03f,z),UnityEngine.Color.magenta);line(marker.Key,new UnityEngine.Vector3(x,.03f,z-.15f),new UnityEngine.Vector3(x,.03f,z+.15f),UnityEngine.Color.magenta);}
        foreach(var g in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects()){var m=g.GetComponent<P2SCV1Object>();if(m==null||m.objectId=="Floor")continue;var label=new UnityEngine.GameObject("ID label "+m.objectId);label.transform.SetParent(g.transform,false);label.transform.localPosition=new UnityEngine.Vector3(0,.58f,0);label.transform.localRotation=UnityEngine.Quaternion.Euler(90,0,0);label.transform.localScale=new UnityEngine.Vector3(.3f,.3f,.3f);var tm=label.AddComponent<UnityEngine.TextMesh>();tm.text=m.objectId;tm.characterSize=.5f;tm.fontSize=40;tm.anchor=UnityEngine.TextAnchor.MiddleCenter;tm.color=UnityEngine.Color.black;}
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());return true;'''.replace('DATA',json.dumps(encoded))
        self.evaluate(code)
    def render(self,path,top=False):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);ready=Path(str(path)+'.ready');ready.unlink(missing_ok=True)
        position='new UnityEngine.Vector3(0,18,0)' if top else 'new UnityEngine.Vector3(10,12,-13)'
        aim='c.transform.rotation=UnityEngine.Quaternion.Euler(90,0,0);' if top else 'c.transform.LookAt(new UnityEngine.Vector3(0,1,0));'
        code='''var g=new UnityEngine.GameObject("V2 temporary camera");g.hideFlags=UnityEngine.HideFlags.HideAndDontSave;var c=g.AddComponent<UnityEngine.Camera>();c.transform.position=POSITION;AIM c.orthographic=true;c.orthographicSize=7.8f;c.clearFlags=UnityEngine.CameraClearFlags.SolidColor;c.backgroundColor=new UnityEngine.Color(.91f,.93f,.95f);var lg=new UnityEngine.GameObject("V2 temporary light");lg.hideFlags=UnityEngine.HideFlags.HideAndDontSave;var l=lg.AddComponent<UnityEngine.Light>();l.type=UnityEngine.LightType.Directional;l.intensity=1.8f;l.transform.rotation=UnityEngine.Quaternion.Euler(45,-35,0);UnityEngine.RenderSettings.ambientLight=new UnityEngine.Color(.65f,.65f,.65f);var rt=new UnityEngine.RenderTexture(1200,900,24);var prev=UnityEngine.RenderTexture.active;try{c.targetTexture=rt;c.Render();UnityEngine.RenderTexture.active=rt;var t=new UnityEngine.Texture2D(1200,900,UnityEngine.TextureFormat.RGB24,false);t.ReadPixels(new UnityEngine.Rect(0,0,1200,900),0,0);t.Apply();System.IO.File.WriteAllBytes(PATH,t.EncodeToPNG());UnityEngine.Object.DestroyImmediate(t);}finally{UnityEngine.RenderTexture.active=prev;c.targetTexture=null;rt.Release();UnityEngine.Object.DestroyImmediate(rt);UnityEngine.Object.DestroyImmediate(g);UnityEngine.Object.DestroyImmediate(lg);}System.IO.File.WriteAllText(PATH+".ready","complete");return true;'''.replace('POSITION',position).replace('AIM',aim).replace('PATH',json.dumps(str(path)))
        try:self.evaluate(code)
        except RuntimeError as e:
            if 'Main thread operation timed out' not in str(e):raise
        until=time.monotonic()+45
        while not ready.exists() and time.monotonic()<until:time.sleep(.2)
        if not ready.exists():raise RuntimeError('Render did not finish')

def item(o):
    kind=o.get('kind','box')
    if kind in ['pillar','cabinet']:kind='shelf'
    category='甲类' if o['id'] in ['A','D'] else '乙类' if o['id'] in ['B','E'] else '丙类' if o['id'] in ['C','F'] else 'fixed'
    return dict(id=o['id'],name=o['id'],kind=kind,category=category,parent='',position=o['position'],rotation=[0,o['yaw'],0],scale=o['size'])

def public_task(d):
    c={k:d.get(k,[]) for k in ['id','scene','allowed','request','regions','keepout','inside','support','facing','relative','distance']}
    c['markers']=d.get('markers',{});c['initial_state_ref']=d['id']+'_initial';c['contract_version']=digest(c)
    c['grounded']=list(d['allowed']) if d['scene']=='M' else d.get('grounded',[])
    c['definitions']={'containment_tolerance_m':.005,'support_height_tolerance_m':.01,'penetration_tolerance_m':.001,'protected_position_tolerance_m':.005,'protected_rotation_tolerance_deg':.5,'scale_tolerance':.00001,'facing_angle_deg':10,'semantic_front':'local +Z, evaluated on XZ','workspace':{'x':[-7,7],'z':[-6,6]},'inventory':'All initial IDs and counts unchanged; no create/delete/scale/reparent','collision_pairs':'all target-target and target-fixed entities except Floor','regions':'full current world AABB containment, closed endpoints','facing_reference':'CURRENT object center or fixed public marker; never initial table center'}
    c['contract_version']=digest(c)
    initial=dict(objects=[item(o) for o in d['initial'].values()])
    initial['objects'].append(dict(id='Floor',name='Floor',kind='floor',category='fixed',parent='',position=[0,-.1,0],rotation=[0,0,0],scale=[14,.2,12]))
    return dict(id=d['id'],contract=c,initial=initial,witness=d['witness'])
