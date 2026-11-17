"""Online diagnostics: evaluate the immutable PUBLIC contract on a real snapshot."""
import itertools
import math

def by_id(state):
    return {o['id']:o for o in state['objects']}

def angle(a,b):
    dot=abs(sum(x*y for x,y in zip(a,b)))
    return math.degrees(2*math.acos(min(1,dot)))

def differences(current,initial,contract):
    now=by_id(current);old=by_id(initial);rows=[]
    for oid in sorted(set(now)|set(old)):
        if oid not in old or oid not in now:
            rows.append(dict(object=oid,field='existence',authorized=False,before=oid in old,after=oid in now));continue
        a=old[oid];b=now[oid];allow=contract['allowed'].get(oid,[])
        full_locked=not any(v in allow for v in ['x','y','z'])
        if full_locked and math.dist(a['position'],b['position'])>.0050001:
            rows.append(dict(object=oid,field='position',before=a['position'],after=b['position'],authorized=False))
        for i,k in enumerate(['x','y','z']):
            if abs(a['position'][i]-b['position'][i])>.0050001 and (not full_locked or k in allow):
                rows.append(dict(object=oid,field='position.'+k,before=a['position'][i],after=b['position'][i],authorized=k in allow))
        if angle(a['quaternion'],b['quaternion'])>.500001:
            legal='yaw' in allow and all(abs((b['rotation'][i]-a['rotation'][i]+180)%360-180)<=.500001 for i in [0,2])
            rows.append(dict(object=oid,field='rotation',before=a['rotation'],after=b['rotation'],authorized=legal))
        for field in ['scale','name','kind','category','parent']:
            different=max(abs(x-y) for x,y in zip(a[field],b[field]))>.00001 if field=='scale' else a[field]!=b[field]
            if different:rows.append(dict(object=oid,field=field,before=a[field],after=b[field],authorized=False))
    return rows

def check(state,initial,c):
    objects=by_id(state);before=by_id(initial);regions={r['id']:r for r in c['regions']};out=[]
    def add(rule,ok,measured,expected):out.append(dict(rule_id=rule,passed=bool(ok),measured=measured,expected=expected))
    add('inventory',len(objects)==len(state['objects']) and set(objects)==set(before),list(objects),sorted(before))
    for oid,rid in c['inside']:
        o=objects[oid];r=regions[rid]
        margins=[o['bounds_min'][j]-r['min'][j] for j in range(3)]+[r['max'][j]-o['bounds_max'][j] for j in range(3)]
        add('inside:'+oid+':'+rid,min(margins)>=-.0050001,dict(min=o['bounds_min'],max=o['bounds_max'],minimum_margin=min(margins)),r)
    for oid,support in c['support']:
        o=objects[oid];s=objects[support];gap=o['bounds_min'][1]-s['bounds_max'][1]
        inside=all(o['bounds_min'][j]>=s['bounds_min'][j]-.0050001 and o['bounds_max'][j]<=s['bounds_max'][j]+.0050001 for j in [0,2])
        add('support:'+oid,abs(gap)<=.0100001 and inside,dict(vertical_gap=gap,horizontally_contained=inside),dict(support=support,height_tolerance=.01))
    if c['scene']=='M' or c['scene']=='D':
        for oid in c['grounded']:
            gap=objects[oid]['bounds_min'][1]
            add('ground:'+oid,abs(gap)<=.0100001,gap,dict(ground_y=0,tolerance=.01))
    for oid,target in c['facing']:
        o=objects[oid];point=c.get('markers',{}).get(target,objects[target]['position'] if target in objects else None)
        q=o['quaternion'];heading=math.atan2(2*(q[0]*q[2]+q[3]*q[1]),1-2*(q[0]**2+q[1]**2))
        dx=point[0]-o['position'][0];dz=point[2]-o['position'][2]
        error=abs(math.degrees(math.atan2(math.sin(heading-math.atan2(dx,dz)),math.cos(heading-math.atan2(dx,dz)))))
        defined=math.hypot(dx,dz)>1e-9
        signed=math.degrees(math.atan2(math.sin(math.atan2(dx,dz)-heading),math.cos(math.atan2(dx,dz)-heading))) if defined else None
        add('facing:'+oid,defined and error<=10.00001,
            dict(angle_degrees=error,current_yaw_deg=math.degrees(heading)%360,signed_error_deg=signed,target_point=point,direction_defined=defined),
            dict(target=target,max_angle_degrees=10,yaw_update_rule='yaw_next=(current_yaw_deg+signed_error_deg)%360; signed_error_deg is a relative correction, not an absolute yaw'))
    for group in c['relative']:
        for a,b in itertools.combinations(group,2):
            err=math.dist([objects[a]['position'][j]-objects[b]['position'][j] for j in range(3)],[before[a]['position'][j]-before[b]['position'][j] for j in range(3)])
            add('relative:'+a+':'+b,err<=.0050001,err,.005)
    for group,minimum in c['distance']:
        for a,b in itertools.combinations(group,2):
            dist=math.hypot(objects[a]['position'][0]-objects[b]['position'][0],objects[a]['position'][2]-objects[b]['position'][2])
            add('distance:'+a+':'+b,dist>=minimum-.0050001,dist,dict(minimum=minimum,metric='XZ center distance'))
    for a,b in itertools.combinations(sorted(objects),2):
        if 'Floor' in [a,b]:continue
        if a not in c['allowed'] and b not in c['allowed']:continue
        depths=[min(objects[a]['bounds_max'][j],objects[b]['bounds_max'][j])-max(objects[a]['bounds_min'][j],objects[b]['bounds_min'][j]) for j in range(3)]
        add('nonoverlap:'+a+':'+b,min(depths)<=.0010001,depths,dict(max_axis_intersection=.001))
    for oid in c['allowed']:
        o=objects[oid]
        add('workspace:'+oid,all(o['bounds_min'][j]>=v[0]-.0050001 and o['bounds_max'][j]<=v[1]+.0050001 for j,v in [(0,[-7,7]),(2,[-6,6])]),dict(min=o['bounds_min'],max=o['bounds_max']),dict(x=[-7,7],z=[-6,6]))
        for r in c['keepout']:
            depths=[min(o['bounds_max'][j],r['max'][j])-max(o['bounds_min'][j],r['min'][j]) for j in range(3)]
            add('clear:'+oid+':'+r['id'],min(depths)<=.0010001,depths,dict(region=r,max_intersection=.001))
    unauthorized=[x for x in differences(state,initial,c) if not x['authorized']]
    add('permissions',not unauthorized,unauthorized,c['allowed'])
    return dict(passed=all(x['passed'] for x in out),rules=out)

def compare(state,initial,contract):
    rows=differences(state,initial,contract)
    return dict(passed=all(r['authorized'] for r in rows),differences=rows,initial_state_ref=contract['initial_state_ref'])
