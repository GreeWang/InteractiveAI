"""Research-only readback via official MCP eval; never an actor-facing wrapper."""
import hashlib
import json

CODE=r'''
var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
var roots=scene.GetRootGameObjects();
var nodes=new System.Collections.Generic.List<UnityEngine.GameObject>();
var keys=new System.Collections.Generic.Dictionary<int,string>();
System.Action<UnityEngine.Transform,string> visit=null;
visit=(t,k)=>{var mark=t.GetComponent<P2SCV1Object>();if(mark!=null)k="entity:"+mark.objectId;nodes.Add(t.gameObject);keys[t.gameObject.GetInstanceID()]=k;for(int i=0;i<t.childCount;i++)visit(t.GetChild(i),k+"/child:"+i);};
for(int i=0;i<roots.Length;i++)visit(roots[i].transform,"root:"+i);
foreach(var g in nodes){var comps=g.GetComponents<UnityEngine.Component>();for(int i=0;i<comps.Length;i++)if(comps[i]!=null)keys[comps[i].GetInstanceID()]=keys[g.GetInstanceID()]+"/component:"+comps[i].GetType().FullName+":"+i;}
System.Func<UnityEngine.Object,string> key=(o)=>{if(o==null)return "null";if(keys.ContainsKey(o.GetInstanceID()))return keys[o.GetInstanceID()];string guid;long fileid;if(UnityEditor.AssetDatabase.TryGetGUIDAndLocalFileIdentifier(o,out guid,out fileid))return "asset:"+guid+":"+fileid;return o.GetType().FullName+":"+o.name;};
System.Func<string,string> normalize=(text)=>System.Text.RegularExpressions.Regex.Replace(text,@"""instanceID""\s*:\s*(-?\d+)",m=>"\"reference\":"+Newtonsoft.Json.JsonConvert.SerializeObject(key(UnityEditor.EditorUtility.InstanceIDToObject(int.Parse(m.Groups[1].Value)))));
var protectedState=new System.Collections.Generic.SortedDictionary<string,string>(System.StringComparer.Ordinal);
var shapes=new System.Collections.Generic.Dictionary<int,string>();
foreach(var g in nodes){
    var nodeKey=keys[g.GetInstanceID()];
    protectedState[nodeKey+"/UnityEngine.GameObject"]=normalize(UnityEditor.EditorJsonUtility.ToJson(g));
    foreach(var c in g.GetComponents<UnityEngine.Component>()){
        if(c==null){protectedState[nodeKey+"/missing_script"]="true";continue;}
        var data=Newtonsoft.Json.Linq.JObject.Parse(UnityEditor.EditorJsonUtility.ToJson(c));
        if(c is UnityEngine.Transform && g.GetComponent<P2SCV1Object>()!=null){var transformData=data["Transform"] as Newtonsoft.Json.Linq.JObject ?? data;foreach(var p in new[]{"m_LocalPosition","m_LocalRotation","m_LocalScale","m_LocalEulerAnglesHint"})transformData.Remove(p);}
        protectedState[key(c)]=normalize(data.ToString(Newtonsoft.Json.Formatting.None));
    }
    var filter=g.GetComponent<UnityEngine.MeshFilter>();
    if(filter!=null && filter.sharedMesh!=null){var mesh=filter.sharedMesh;if(!shapes.ContainsKey(mesh.GetInstanceID()))shapes[mesh.GetInstanceID()]=Newtonsoft.Json.JsonConvert.SerializeObject(new{vertices=mesh.vertices.Select(v=>new[]{v.x,v.y,v.z}).ToArray(),triangles=mesh.triangles,normals=mesh.normals.Select(v=>new[]{v.x,v.y,v.z}).ToArray()});protectedState[nodeKey+"/mesh_geometry"]=shapes[mesh.GetInstanceID()];}
    var renderer=g.GetComponent<UnityEngine.Renderer>();
    if(renderer!=null){var mats=renderer.sharedMaterials;for(int i=0;i<mats.Length;i++)if(mats[i]!=null)protectedState[nodeKey+"/material:"+i]=normalize(UnityEditor.EditorJsonUtility.ToJson(mats[i]));}
}
System.Func<UnityEngine.Vector3,float[]> a=(v)=>new[]{v.x,v.y,v.z};
var objects=nodes.Select(g=>g.GetComponent<P2SCV1Object>()).Where(m=>m!=null).OrderBy(m=>m.objectId,System.StringComparer.Ordinal).Select(m=>{
    var t=m.transform;var renderer=m.GetComponent<UnityEngine.Renderer>();var b=renderer!=null?renderer.bounds:new UnityEngine.Bounds(t.position,UnityEngine.Vector3.zero);var q=t.rotation;
    return new{id=m.objectId,name=m.gameObject.name,kind=m.kind,category=m.category,parent=t.parent?t.parent.name:"",position=a(t.position),rotation=a(t.eulerAngles),quaternion=new[]{q.x,q.y,q.z,q.w},scale=a(t.localScale),bounds_min=a(b.min),bounds_max=a(b.max)};
}).ToArray();
return Newtonsoft.Json.JsonConvert.SerializeObject(new{objects=objects,protected_state=protectedState,scene=scene.path,playing=UnityEditor.EditorApplication.isPlaying,paused=UnityEditor.EditorApplication.isPaused});
'''


def decode(result):
    if result.get('isError'):raise RuntimeError('Official MCP returned error: '+str(result)[:1000])
    blocks=[c['text'] for c in result.get('content',[]) if c.get('type')=='text']
    if len(blocks)!=1:raise RuntimeError('Unexpected MCP text result envelope')
    return json.loads(blocks[0])


def snapshot(mcp,version=0):
    result=mcp.call('eval',dict(code=CODE,timeout=30000));payload=decode(result)
    if not payload.get('success'):raise RuntimeError(str(payload)[:2000])
    state=json.loads(payload['result']);state['state_version']=version;return state


def geometry(state):return dict(objects=state['objects'],state_version=state.get('state_version',0))


def digest(state):
    return hashlib.sha256(json.dumps(dict(objects=state['objects'],protected_state=state['protected_state']),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def protected_diff(state,initial):
    now=state['protected_state'];old=initial['protected_state'];rows=[]
    for k in sorted(set(now)|set(old)):
        if now.get(k)!=old.get(k):rows.append(dict(object=k,field='protected_scene_structure_or_component',before=old.get(k),after=now.get(k),authorized=False))
    if state['playing'] or state['paused']:rows.append(dict(object='Editor',field='edit_mode',before='edit',after='play_or_pause',authorized=False))
    return rows


if __name__=='__main__':
    from common import ROOT,read,write
    from mcp_stdio import MCP
    cfg=read(ROOT/'config.json');m=MCP(cfg['project'],ROOT/'probe/observer_rpc.ndjson')
    try:
        s=snapshot(m);write(ROOT/'probe/initial_observer.json',s);other=snapshot(m)
        print('Observed',len(s['objects']),'task entities;',len(s['protected_state']),'protected records; repeated stable',digest(s)==digest(other))
        print('Probe bound',next(x for x in s['objects'] if x['id']=='D05Table')['bounds_min'])
    finally:m.close()
