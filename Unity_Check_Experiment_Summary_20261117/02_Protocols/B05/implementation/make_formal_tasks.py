"""Twelve fixed new layouts, six families, two difficulty levels; no model calls."""
import copy
import math
from common import ROOT,write
from engine import public_task
from online_check import check
from offline_score import score


def obj(oid,p,size,yaw=0,kind='box'):
    return dict(id=oid,position=p,size=size,yaw=yaw,kind=kind)


def base(tid,scene,family,hard,request):
    positions=[[x,.8,z] for x in [-6.1,6.1] for z in [-4.5,-1.4,1.7,4.8]]+[[-3.6,.8,-5.25],[.6,.8,-5.25]]
    fixed={f'{tid}Fixed{i}':obj(f'{tid}Fixed{i}',p,[.55,1.6,.55],kind='shelf') for i,p in enumerate(positions)}
    return dict(id=tid,scene=scene,family=family,difficulty='困难' if hard else '中等',request=request,initial=fixed,witness={},allowed={},regions=[],keepout=[],inside=[],support=[],grounded=[],facing=[],relative=[],distance=[],markers={})


def add(t,oid,initial,size,fields,final,yaw=0,initial_yaw=0,kind='box'):
    t['initial'][oid]=obj(oid,initial,size,initial_yaw,kind);t['allowed'][oid]=fields
    t['witness'][oid]=obj(oid,final,size,yaw,kind)


def slot(t,oid,name,p,ex,ez,y0,y1):
    t['regions'].append(dict(id=name,min=[p[0]-ex,y0,p[2]-ez],max=[p[0]+ex,y1,p[2]+ez]));t['inside'].append([oid,name])


def corridor(t,front_only=False):
    t['keepout']=[dict(id=t['id']+'保留通道',min=[-.35,0,-5],max=[.35,4,-.5 if front_only else 5])]


def rigid(hard):
    tid='V3M02' if hard else 'V3M01'
    t=base(tid,'M','meeting_rigid',hard,'将主桌与四把椅子整组平移到目标活动区。只允许各自X、Z位置变化；两两相对位移、Y、yaw和其他字段保持初始值。所有完整实际包围盒都须在区内、接地、不重叠，并避开固定设施和保留通道。')
    cx,cz=(2.55,2.55) if hard else (2.45,2.25);width,depth,height=(2.02,1.22,1.42) if hard else (1.7,1.02,1.24)
    add(t,tid+'Table',[-3.25,height/2,-2.35],[width,height,depth],['x','z'],[cx,height/2,cz],kind='table')
    dx,dz,seat,h=(.86,1.4,.62,1.04) if hard else (.72,1.15,.48,.96)
    for i,(x,z,yaw) in enumerate([(-dx,-dz,0),(dx,-dz,0),(-dx,dz,180),(dx,dz,180)],1):
        add(t,tid+f'Seat{i}',[-3.25+x,h/2,-2.35+z],[seat,h,seat],['x','z'],[cx+x,h/2,cz+z],yaw,yaw,'chair')
    lo,hi=([1.30,-.01,.76],[3.80,1.8,4.34]) if hard else ([1.18,-.01,.55],[3.8,1.55,3.95])
    t['regions']=[dict(id=tid+'活动区',min=lo,max=hi)];t['inside']=[[o,tid+'活动区'] for o in t['allowed']];t['relative']=[list(t['allowed'])];corridor(t)
    if hard:t['initial'][tid+'Pedestal']=obj(tid+'Pedestal',[2.55,.3,1.05],[.36,.6,.32],kind='shelf')
    return t


def dynamic(hard):
    tid='V3M04' if hard else 'V3M03';target=[-1.55,.76,2.65] if hard else [1.35,.68,2.35]
    t=base(tid,'M','meeting_facing',hard,'按指定区域布置桌椅，每把椅子都面向桌子当前中心，按旋转后的完整包围盒验收。困难题的主桌也必须移入桌区；固定题的主桌不得修改。椅子间XZ中心距离至少1.1米。全部目标接地、不与彼此及固定设施重叠，避开保留区；未授权对象和字段保持初始值。')
    table=tid+'Table';size=[2.08,1.52,1.32] if hard else [1.86,1.36,1.08]
    if hard:
        add(t,table,[-3.55,.76,-2.25],size,['x','z'],target,kind='table')
        t['regions'].append(dict(id=tid+'桌区',min=[-2.9,-.01,1.6],max=[-.2,1.8,3.7]));t['inside'].append([table,tid+'桌区'])
    else:t['initial'][table]=obj(table,target,size,kind='table')
    goals=[[-3.05,1],[-.05,1],[-3.05,4.3],[-.05,4.3]] if hard else [[0,.85],[2.7,.85],[0,3.85],[2.7,3.85]]
    chairs=[]
    for i,(x,z) in enumerate(goals,1):
        oid=tid+f'Seat{i}';h=1.08 if hard else .98;sz=[.62,h,.54] if hard else [.52,h,.52];p=[x,h/2,z]
        yaw=math.degrees(math.atan2(target[0]-x,target[2]-z))%360
        add(t,oid,[-4.8+1.4*(i-1),h/2,-2.6],sz,['x','z','yaw'],p,yaw,0,'chair');chairs.append(oid)
        slot(t,oid,tid+f'座区{i}',p,.46 if hard else .44,.46 if hard else .44,-.01,1.6);t['facing'].append([oid,table])
    t['distance']=[[chairs,1.1]];corridor(t,True)
    return t


def permissions(hard):
    tid='V3M06' if hard else 'V3M05';target=[.55,.74,2.65] if hard else [-.65,.7,2.2]
    t=base(tid,'M','meeting_permissions',hard,'调整指定椅子并全部面向固定主桌当前中心。严格遵守allowed字段：yaw-only椅子位置不变，XZ-only椅子朝向不变，其他目标仅改允许字段。可移动椅子的完整包围盒须在各自座区，全部椅子接地、互不重叠且XZ中心间距至少1.1米，避开固定设施和保留区。桌和其他对象全部保持初始状态。')
    table=tid+'Table';t['initial'][table]=obj(table,target,[2.24,1.48,1.28] if hard else [2,1.4,1.1],kind='table')
    goals=[[-1.1,1.05],[2.2,1.05],[-1.1,4.25],[2.2,4.25],[-1.28,2.65],[2.38,2.65]] if hard else [[-2,.65],[.7,.65],[-2.2,3.8],[.9,3.8]]
    for i,(x,z) in enumerate(goals,1):
        fields=['yaw'] if i in [3,4] else ['x','z'] if i>=5 else ['x','z','yaw'];h=1.06 if hard else 1.;w=.58 if hard else .52;p=[x,h/2,z]
        yaw=math.degrees(math.atan2(target[0]-x,target[2]-z))%360
        initial=p[:] if fields==['yaw'] else [-4.6+1.3*(i-1),h/2,-2.8 if i<=2 else -.9]
        iyaw=yaw if fields==['x','z'] else 90 if fields==['yaw'] else 0;oid=tid+f'Seat{i}'
        add(t,oid,initial,[w,h,w],fields,p,yaw,iyaw,'chair');t['facing'].append([oid,table])
        if fields!=['yaw']:slot(t,oid,tid+f'座区{i}',p,.33 if i>=5 else .46,.33 if i>=5 else .46,-.01,1.6)
    t['distance']=[[list(t['allowed']),1.1]];corridor(t,True);return t


def packing(hard):
    tid='V3W02' if hard else 'V3W01';t=base(tid,'W','warehouse_packing',hard,'把全部目标箱放入统一目标区并由固定平台完整支撑。只允许修改XYZ，不允许改yaw。按完整包围盒验收，底面须贴合平台顶面，无浮空、穿透、箱间重叠，XZ中心间距至少0.9米，并避开保留通道。其余对象及字段不变。')
    platform=tid+'Rack';center=[-2.45,.83,2.75] if hard else [2.65,.64,2.55];size=[3.7,1.66,2.65] if hard else [3.6,1.28,2.1];top=size[1]
    t['initial'][platform]=obj(platform,center,size,kind='table')
    sizes=[[.95,.83,.75],[1.02,.68,.68],[.72,.96,.86],[1.16,.72,.94],[1.25,1.12,.92]] if hard else [[.86,.62,.72],[.68,.88,.94],[.76,.54,.65]]
    points=[[-3.55,2],[-2.28,2],[-1.21,2],[-3.42,3.28],[-1.76,3.28]] if hard else [[1.55,2.55],[2.65,2.55],[3.75,2.55]]
    for i,(s,(x,z)) in enumerate(zip(sizes,points),1):
        oid=tid+f'Box{i}';add(t,oid,[-4.4+2.1*(i-1),s[1]/2,-3.1],s,['x','y','z'],[x,top+s[1]/2,z]);t['support'].append([oid,platform])
    lo,hi=([-4.2,1.65,1.49],[-.7,2.85,4.0]) if hard else ([1,1.27,1.6],[4.3,2.6,3.5]);t['regions']=[dict(id=tid+'装架区',min=lo,max=hi)];t['inside']=[[o,tid+'装架区'] for o in t['allowed']];t['distance']=[[list(t['allowed']),.9]];corridor(t);return t


def levels(hard):
    tid='V3W04' if hard else 'V3W03';t=base(tid,'W','warehouse_support',hard,'将每个目标箱分配到inside和support指定的层区与固定平台上。只允许XYZ，yaw及其他字段不变。底面贴合各自平台实际顶面，完整包围盒在指定区域内，无浮空、穿透及重叠，并避开保留通道。所有支撑平台、固定设施保持初始状态。')
    platforms=[([-3.85,.65,2.5],[2.05,1.3,2.2]),([-.5,1.05,2.8],[2.2,2.1,2.05]),([3.05,1.45,2.45],[2.35,2.9,2.3])] if hard else [([-2.5,.55,2.3],[2.9,1.1,1.9]),([2.2,1.18,2.8],[2.7,2.36,2])]
    sizes=[[.72,.52,.76],[.66,.84,.68],[.70,.72,.68],[.72,1.02,.82],[.78,.62,.86],[.70,1.10,.92]] if hard else [[.9,.65,.72],[.8,.8,.92],[.88,.55,.7],[.72,.96,.86]]
    xs=[-4.38,-3.32,-1.05,.05,2.5,3.63] if hard else [-3.2,-1.85,1.55,2.85]
    for j,(p,sz) in enumerate(platforms):
        name=tid+f'Platform{j+1}';t['initial'][name]=obj(name,p,sz,kind='table');top=sz[1]
        rid=tid+f'层区{j+1}';t['regions'].append(dict(id=rid,min=[p[0]-sz[0]/2+.06,top-.01,p[2]-sz[2]/2+.06],max=[p[0]+sz[0]/2-.06,top+1.25,p[2]+sz[2]/2-.06]))
        for k in range(2):
            i=j*2+k;s=sizes[i];oid=tid+f'Box{i+1}'
            add(t,oid,[-4.5+1.8*i,s[1]/2,-3.6],s,['x','y','z'],[xs[i],top+s[1]/2,p[2]])
            t['inside'].append([oid,rid]);t['support'].append([oid,name])
    corridor(t,True);return t


def footprint(hard):
    tid='V3W06' if hard else 'V3W05';t=base(tid,'W','warehouse_footprint',hard,'把目标长方体箱完整放入各自窄槽并由指定固定平台支撑，同时面向各自公开Aim标记。允许XYZ和yaw，按旋转后的实际世界包围盒验收。底面贴合平台，目标互不重叠、XZ中心间距至少1米，避开保留通道。所有未授权对象及字段保持初始值。')
    platforms=[([-2.65,.78,2.8],[3.25,1.56,2.75]),([2.8,1.12,2.55],[3.45,2.24,2.75])] if hard else [([2.5,.72,2.7],[3.7,1.44,2.9])]
    points=[[-3.6,2.1],[-1.65,2.1],[-2.65,3.5],[1.85,1.95],[3.85,1.95],[2.8,3.3]] if hard else [[1.5,2],[3.5,2],[1.5,3.4],[3.5,3.4]]
    sizes=[[1.25,.7,.42],[1.18,.54,.48],[1.34,.92,.5],[1.30,.6,.46],[1.2,.82,.44],[1.4,.74,.52]] if hard else [[1.1,.58,.44],[1.2,.72,.48],[1.15,.64,.42],[1.05,.5,.46]]
    yaws=[90,270,180,270,90,0] if hard else [90,270,0,180]
    for j,(p,s) in enumerate(platforms):t['initial'][tid+f'Platform{j+1}']=obj(tid+f'Platform{j+1}',p,s,kind='table')
    for i,((x,z),s,yaw) in enumerate(zip(points,sizes,yaws),1):
        j=0 if not hard or i<=3 else 1;top=platforms[j][1][1];oid=tid+f'Box{i}';p=[x,top+s[1]/2,z]
        add(t,oid,[-4.7+1.9*(i-1),s[1]/2,-2.9],s,['x','y','z','yaw'],p,yaw)
        is_side=yaw in [90,270];slot(t,oid,tid+f'窄槽{i}',p,.32 if is_side else .78,.71 if is_side else .35,top-.01,top+1.3)
        t['support'].append([oid,tid+f'Platform{j+1}']);marker=tid+f'Aim{i}';a=math.radians(yaw);t['markers'][marker]=[x+1.1*math.sin(a),.05,z+1.1*math.cos(a)];t['facing'].append([oid,marker])
    t['distance']=[[list(t['allowed']),1.0]];corridor(t);return t


def numeric_state(objects):
    out=copy.deepcopy(objects)
    for o in out:
        a=math.radians(o['rotation'][1]);sx,sy,sz=o['scale'];ext=[(abs(math.cos(a))*sx+abs(math.sin(a))*sz)/2,sy/2,(abs(math.sin(a))*sx+abs(math.cos(a))*sz)/2]
        o['quaternion']=[0,math.sin(a/2),0,math.cos(a/2)];o['bounds_min']=[p-e for p,e in zip(o['position'],ext)];o['bounds_max']=[p+e for p,e in zip(o['position'],ext)]
    return dict(objects=out,state_version=0)


if __name__=='__main__':
    designs=[f(h) for f in [rigid,dynamic,permissions,packing,levels,footprint] for h in [False,True]]
    for d in designs:
        t=public_task(d);initial=numeric_state(t['initial']['objects']);reference=copy.deepcopy(initial)
        for o in reference['objects']:
            if o['id'] in d['witness']:
                v=d['witness'][o['id']];o['position']=v['position'];o['rotation']=[0,v['yaw'],0]
        reference=numeric_state(reference['objects']);g=score(reference,initial,t['contract'])
        assert g['success'],(d['id'],[x['rule_id'] for x in g['checks'] if not x['passed']])
        assert check(reference,initial,t['contract'])['passed'] and not score(initial,initial,t['contract'])['success']
        write(ROOT/'tasks'/(d['id']+'.json'),t)
    write(ROOT/'task_design.json',dict(tasks=designs,scope='New fixed formal layouts constructed before any formal model calls; six task families, medium/hard pair per family'))
    write(ROOT/'task_manifest.json',dict(formal=[d['id'] for d in designs],development=[],families={d['family']:[v['id'] for v in designs if v['family']==d['family']] for d in designs}))
    print('Created 12 new tasks; numeric witnesses pass; actual Unity preflight still required')
