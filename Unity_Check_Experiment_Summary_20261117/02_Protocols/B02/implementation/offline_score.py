"""Private scorer. Separate predicates; never used to supply model feedback."""
import math

def score(state,initial,c):
    cur={o['id']:o for o in state['objects']};old={o['id']:o for o in initial['objects']};rows=[]
    def record(id,ok,kind='target',**m):rows.append(dict(rule_id=id,passed=bool(ok),category=kind,measurement=m))
    record('inventory',set(cur)==set(old) and len(cur)==len(state['objects']))
    for oid,base in old.items():
        if oid not in cur:record('preserve:'+oid,False,'protection');continue
        o=cur[oid];allow=c['allowed'].get(oid,[])
        if not any(a in allow for a in ['x','y','z']):
            d=sum((o['position'][j]-base['position'][j])**2 for j in range(3))**.5
            record('preserve:'+oid+':position',d<=.0050001,'protection',error=d)
        else:
            for j,axis in enumerate(['x','y','z']):
                if axis not in allow:record('preserve:'+oid+':'+axis,abs(o['position'][j]-base['position'][j])<=.0050001,'protection')
        if 'yaw' not in allow:
            cosine=abs(sum(o['quaternion'][j]*base['quaternion'][j] for j in range(4)))
            deg=2*math.acos(max(0,min(1,cosine)))*180/math.pi
            record('preserve:'+oid+':rotation',deg<=.500001,'protection',angle=deg)
        else:
            record('preserve:'+oid+':roll_pitch',all(min((o['rotation'][j]-base['rotation'][j])%360,(base['rotation'][j]-o['rotation'][j])%360)<=.500001 for j in [0,2]),'protection')
        record('preserve:'+oid+':scale',all(abs(x-y)<=.00001 for x,y in zip(o['scale'],base['scale'])),'protection')
        for k in ['name','kind','category','parent']:record('preserve:'+oid+':'+k,o[k]==base[k],'protection')
    if set(cur)!=set(old):return dict(success=False,protection_violation=True,checks=rows)
    region_map={r['id']:r for r in c['regions']}
    for oid,rid in c['inside']:
        b=cur[oid];r=region_map[rid]
        ok=all(b['bounds_min'][k]+.0050001>=r['min'][k] and b['bounds_max'][k]-.0050001<=r['max'][k] for k in range(3))
        record('inside:'+oid+':'+rid,ok)
    for oid,sid in c['support']:
        o=cur[oid];s=cur[sid];height=o['bounds_min'][1]-s['bounds_max'][1]
        footprint=min([o['bounds_min'][k]-s['bounds_min'][k] for k in [0,2]]+[s['bounds_max'][k]-o['bounds_max'][k] for k in [0,2]])
        record('support:'+oid,-.0100001<=height<=.0100001 and footprint>=-.0050001,gap=height,margin=footprint)
    for oid in c['grounded']:record('ground:'+oid,abs(cur[oid]['bounds_min'][1])<=.0100001)
    for oid,reference in c['facing']:
        o=cur[oid];point=c.get('markers',{}).get(reference,cur[reference]['position'] if reference in cur else None)
        x,y,z,w=o['quaternion'];v=[2*(x*z+w*y),1-2*(x*x+y*y)];t=[point[0]-o['position'][0],point[2]-o['position'][2]]
        norm=math.sqrt(sum(a*a for a in v)*sum(a*a for a in t));a=180 if norm<1e-12 else math.degrees(math.acos(max(-1,min(1,sum(a*b for a,b in zip(v,t))/norm))))
        record('facing:'+oid,a<=10.00001,angle=a)
    for group in c['relative']:
        for i,a in enumerate(group):
            for b in group[i+1:]:
                err=sum(((cur[a]['position'][k]-cur[b]['position'][k])-(old[a]['position'][k]-old[b]['position'][k]))**2 for k in range(3))**.5
                record('relative:'+a+':'+b,err<=.0050001,error=err)
    for group,threshold in c['distance']:
        for i,a in enumerate(group):
            for b in group[i+1:]:
                squared=sum((cur[a]['position'][k]-cur[b]['position'][k])**2 for k in [0,2])
                record('distance:'+a+':'+b,squared>=max(0,threshold-.0050001)**2)
    ids=sorted(cur)
    for i,a in enumerate(ids):
        if a=='Floor':continue
        for b in ids[i+1:]:
            if b=='Floor' or (a not in c['allowed'] and b not in c['allowed']):continue
            separated=any(cur[a]['bounds_max'][j]<=cur[b]['bounds_min'][j]+.0010001 or cur[b]['bounds_max'][j]<=cur[a]['bounds_min'][j]+.0010001 for j in range(3))
            record('nonoverlap:'+a+':'+b,separated)
    for oid in c['allowed']:
        o=cur[oid]
        record('workspace:'+oid,o['bounds_min'][0]>=-7.0050001 and o['bounds_max'][0]<=7.0050001 and o['bounds_min'][2]>=-6.0050001 and o['bounds_max'][2]<=6.0050001)
        for region in c['keepout']:
            clear=any(o['bounds_max'][k]<=region['min'][k]+.0010001 or region['max'][k]<=o['bounds_min'][k]+.0010001 for k in range(3))
            record('clear:'+oid+':'+region['id'],clear)
    return dict(success=all(x['passed'] for x in rows),protection_violation=any(not x['passed'] for x in rows if x['category']=='protection'),checks=rows)
