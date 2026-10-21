#!/usr/bin/env python3
import json, os, subprocess, sys
proj = os.environ["PROJ"]
mode, pid, cfile, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

def unity_eval(code):
    cmd = ["unity","command","--project-path",proj,"--format","json","--result-only","eval","--","--code",code]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(p.stdout or "{}").get("result","")
    except Exception:
        return p.stdout or ""

if mode == "constraint":
    abs_path = os.path.join(proj, cfile)
    code = f'var r = Prompt2Scene.Check.ConstraintChecker.RunFromPath(@"{abs_path}"); return "success="+r.success+" passed="+r.passed+" failed="+r.failed;'
    raw = unity_eval(code)
    open(out,"w").write(raw if isinstance(raw,str) else json.dumps(raw))
    src = os.path.join(proj, "Logs/prompt2scene-check-last.json")
    if os.path.isfile(src):
        open(out.replace(".json","_report.json"),"wb").write(open(src,"rb").read())
    print("true" if "success=True" in str(raw) else "false")
    sys.exit(0)

codes = {
  "P02": 'var a=GameObject.Find("CubeA").transform.position; var b=GameObject.Find("SphereB").transform.position; var above=(b.y>a.y+0.4f)&&(Mathf.Abs(b.x-a.x)<0.6f)&&(Mathf.Abs(b.z-a.z)<0.6f); return "pass="+above;',
  "H02": 'var a=GameObject.Find("CubeA").transform.position; var b=GameObject.Find("SphereB").transform.position; var above=(b.y>a.y+0.4f)&&(Mathf.Abs(b.x-a.x)<0.6f)&&(Mathf.Abs(b.z-a.z)<0.6f); return "pass="+above;',
  "P03": 'var c=GameObject.Find("CubeC"); if(c==null) return "pass=False"; var a=GameObject.Find("CubeA").transform.position; var d=Vector3.Distance(a,c.transform.position); return "pass="+(d>=1.2f&&d<=1.8f)+";dist="+d;',
  "H03": 'var c=GameObject.Find("SideCube"); if(c==null) return "pass=False"; var a=GameObject.Find("CubeA").transform.position; var d=Vector3.Distance(a,c.transform.position); return "pass="+(d>=1.2f&&d<=1.8f)+";dist="+d;',
  "P09": 'var b=GameObject.Find("SphereB").transform.position; return "pass="+(Mathf.Abs(b.y-2.0f)<0.15f)+";y="+b.y;',
  "H09": 'var b=GameObject.Find("SphereB").transform.position; return "pass="+(Mathf.Abs(b.y-2.0f)<0.15f)+";y="+b.y;',
  "P01": 'var table=GameObject.Find("Table"); var cup=GameObject.Find("Cup"); if(table==null||cup==null) return "pass=False"; var tb=table.transform.position; var cp=cup.transform.position; var horiz=Vector2.Distance(new Vector2(cp.x,cp.z), new Vector2(tb.x,tb.z)); var dy=cp.y-tb.y; return "pass="+((horiz<=0.5f)&&(dy>=0.3f)&&(dy<=1.5f));',
  "H01": 'var table=GameObject.Find("Desk"); var cup=GameObject.Find("Mug"); if(table==null||cup==null) return "pass=False"; var tb=table.transform.position; var cp=cup.transform.position; var horiz=Vector2.Distance(new Vector2(cp.x,cp.z), new Vector2(tb.x,tb.z)); var dy=cp.y-tb.y; return "pass="+((horiz<=0.5f)&&(dy>=0.3f)&&(dy<=1.5f));',
  "P10": 'var a=GameObject.Find("A"); var b=GameObject.Find("B"); var c=GameObject.Find("C"); if(a==null||b==null||c==null) return "pass=False"; var d1=Vector3.Distance(a.transform.position,b.transform.position); var d2=Vector3.Distance(b.transform.position,c.transform.position); return "pass="+((d1>=0.8f&&d1<=1.2f)&&(d2>=0.8f&&d2<=1.2f));',
  "H10": 'var a=GameObject.Find("X"); var b=GameObject.Find("Y"); var c=GameObject.Find("Z"); if(a==null||b==null||c==null) return "pass=False"; var d1=Vector3.Distance(a.transform.position,b.transform.position); var d2=Vector3.Distance(b.transform.position,c.transform.position); return "pass="+((d1>=0.8f&&d1<=1.2f)&&(d2>=0.8f&&d2<=1.2f));',
}
key = pid[:3]
code = codes.get(key) or codes.get(pid[:2])
# better match prefixes
code = None
for k,v in codes.items():
    if pid.startswith(k):
        code = v; break
if not code:
    open(out,"w").write("pass=False;detail=no_postcheck")
    print("false"); sys.exit(0)
raw = unity_eval(code)
open(out,"w").write(str(raw))
print("true" if "pass=True" in str(raw) else "false")
