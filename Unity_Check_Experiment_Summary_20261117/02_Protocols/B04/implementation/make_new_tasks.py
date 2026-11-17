"""Four disjoint long development fixtures; no formal task geometry is reused."""
import copy
import math
from common import ROOT, write
from engine import public_task


def obj(oid, p, size, yaw=0, kind='box'):
    return dict(id=oid, position=p, size=size, yaw=yaw, kind=kind)


def fixed(prefix):
    positions = [[x, .6, z] for x in [-5.8, 5.8] for z in [-4.8, -2, .8, 3.6]]
    positions += [[-3, .6, 5.3], [2.5, .6, 5.3]]
    return {f'{prefix}Fixed{i}': obj(f'{prefix}Fixed{i}', p, [.6, 1.2, .6], kind='shelf') for i, p in enumerate(positions)}


def base(tid, scene, request):
    return dict(id=tid, scene=scene, request=request, initial=fixed(tid), witness={}, allowed={},
                regions=[], keepout=[], inside=[], support=[], grounded=[], facing=[], relative=[], distance=[], markers={})


def add(t, o, allowed, p=None, yaw=None):
    oid = o['id']; t['initial'][oid] = o; t['allowed'][oid] = allowed
    w = copy.deepcopy(o)
    if p is not None: w['position'] = p
    if yaw is not None: w['yaw'] = yaw
    t['witness'][oid] = w


def region(t, oid, name, lower, upper):
    t['regions'].append(dict(id=name, min=lower, max=upper)); t['inside'].append([oid, name])


def build():
    out = []
    t = base('D05', 'M', '将D05Table及D05Seat1至D05Seat4整组移入活动区。只允许各自X、Z平移，保持全部两两相对位移、Y和朝向；完整实际包围盒都须在区内、接地且互不重叠，并避开固定设施和中央保留通道。其余对象及所有未授权字段保持初始状态。')
    table = obj('D05Table', [-3.5,.7,-2.5], [1.8,1.4,1], kind='table')
    add(t, table, ['x','z'], [2.65,.7,2.65])
    for i, (dx,dz,yaw) in enumerate([(-.8,-1.2,0),(.8,-1.2,0),(-.8,1.2,180),(.8,1.2,180)],1):
        add(t,obj(f'D05Seat{i}',[-3.5+dx,.5,-2.5+dz],[.5,1,.5],yaw,'chair'),['x','z'],[2.65+dx,.5,2.65+dz])
    t['initial']['D05Corner'] = obj('D05Corner',[4,.6,1.1],[.6,1.2,.6],kind='shelf')
    t['regions']=[dict(id='D05活动区',min=[1.1,-.01,1],max=[4.2,1.5,4.3])]
    t['inside']=[[i,'D05活动区'] for i in t['allowed']];t['relative']=[list(t['allowed'])]
    t['keepout']=[dict(id='D05通道',min=[-.5,0,-5],max=[.5,3,5])];out.append(t)

    t=base('D06','M','将D06SeatA、D06SeatB分别放入指定座位区并面向固定D06Table；D06SeatC、D06SeatD只允许改yaw，也必须面向当前桌心，位置保持不变。四椅接地、中心XZ间距至少1.2米，完整包围盒不与固定设施或彼此重叠，避开保留区。桌和所有固定对象及未授权字段保持初始值。')
    t['initial']['D06Table']=obj('D06Table',[-.8,.7,2.6],[2,1.4,1.2],kind='table')
    for letter, initial, final, fields in [('A',[-4,.5,-2],[-2.1,.5,.8],['x','z','yaw']),('B',[-2,.5,-2],[.5,.5,.8],['x','z','yaw']),('C',[-2.4,.5,4.3],[-2.4,.5,4.3],['yaw']),('D',[.8,.5,4.3],[.8,.5,4.3],['yaw'])]:
        yaw=math.degrees(math.atan2(-.8-final[0],2.6-final[2]))%360
        oid='D06Seat'+letter;add(t,obj(oid,initial,[.55,1,.55],0,'chair'),fields,final,yaw);t['facing'].append([oid,'D06Table'])
    region(t,'D06SeatA','D06座位A',[-2.7,-.01,.2],[-1.5,1.5,1.4])
    region(t,'D06SeatB','D06座位B',[-.1,-.01,.2],[1.1,1.5,1.4])
    t['distance']=[[list(t['allowed']),1.2]];t['keepout']=[dict(id='D06保留区',min=[2.5,0,-3],max=[3.5,3,3])];out.append(t)

    t=base('D07','W','把D07BoxA、D07BoxB放入D07低层目标区并由固定D07Low完整支撑；D07BoxC、D07BoxD放入D07高层目标区并由固定D07High完整支撑。只改四箱XYZ，不改yaw；底面贴合支撑面且不浮空、不穿透、不互相重叠，避开中央通道。完整实际包围盒须在对应区内，所有固定设施和其他字段保持初始值。')
    t['initial']['D07Low']=obj('D07Low',[-2.3,.7,2.6],[3,1.4,1.8],kind='table')
    t['initial']['D07High']=obj('D07High',[2.6,1.1,2.6],[2.6,2.2,1.8],kind='table')
    for letter,x,size,final,support in [('A',-3,[1,.6,.6],[-2.95,1.7,2.6],'D07Low'),('B',-1.2,[.8,.8,.8],[-1.55,1.8,2.6],'D07Low'),('C',1.5,[.9,.5,.7],[1.95,2.45,2.6],'D07High'),('D',3.5,[.6,.9,.6],[3.1,2.65,2.6],'D07High')]:
        oid='D07Box'+letter;add(t,obj(oid,[x,size[1]/2,-3.5],size),['x','y','z'],final);t['support'].append([oid,support])
    t['regions']=[dict(id='D07低层目标区',min=[-3.6,1.39,1.85],max=[-1,2.5,3.35]),dict(id='D07高层目标区',min=[1.4,2.19,1.8],max=[3.8,3.5,3.4])]
    t['inside']=[[f'D07Box{i}','D07低层目标区' if i in 'AB' else 'D07高层目标区'] for i in 'ABCD']
    t['keepout']=[dict(id='D07通道',min=[-.4,0,-5],max=[.4,4,5])];out.append(t)

    t=base('D08','W','把D08Box1至D08Box6分别完整放入同编号窄槽；前三箱由D08Left支撑，后三箱由D08Right支撑。允许XYZ和yaw，各箱还须面向各自公开标记D08Aim1至D08Aim6，按旋转后的实际包围盒验收。底面贴合支撑、各箱互不重叠、XZ中心间距至少0.8米，并避开中央通道。所有固定设施和其余字段保持初始值。')
    t['initial']['D08Left']=obj('D08Left',[-2.4,.6,2.8],[3.4,1.2,2.4],kind='table')
    t['initial']['D08Right']=obj('D08Right',[2.5,.8,2.8],[3,1.6,2.4],kind='table')
    for i,(x,ix,length,height,depth) in enumerate(zip([-3.55,-2.4,-1.25,1.5,2.5,3.5],[-4,-2.5,-1,1,2.5,4],[1.25,1.3,1.2,1.2,1.35,1.25],[.5,.6,.4,.5,.6,.4],[.45,.5,.4,.45,.5,.4]),1):
        top=1.2 if i<=3 else 1.6;oid=f'D08Box{i}';support='D08Left' if i<=3 else 'D08Right'
        add(t,obj(oid,[ix,height/2,-3.2],[length,height,depth]),['x','y','z','yaw'],[x,top+height/2,2.8],90)
        region(t,oid,f'D08槽{i}',[x-.375,top-.01,1.95],[x+.375,top+1,3.65])
        t['support'].append([oid,support]);t['markers'][f'D08Aim{i}']=[x+.9,.05,2.8];t['facing'].append([oid,f'D08Aim{i}'])
    t['distance']=[[list(t['allowed']),.8]];t['keepout']=[dict(id='D08通道',min=[-.4,0,-5],max=[.4,4,5])];out.append(t)
    return out


if __name__=='__main__':
    tasks=build();write(ROOT/'task_design.json',dict(tasks=tasks,scope='New long development fixtures only; not a confirmatory task set'))
    for t in tasks:write(ROOT/'tasks'/(t['id']+'.json'),public_task(t))
    write(ROOT/'task_manifest.json',dict(formal=[],development=[t['id'] for t in tasks],provenance='D05-D08 use new IDs, dimensions, positions and target regions; older formal tasks untouched'))
    print('Created',[(t['id'],len(t['initial'])+1,len(t['allowed'])) for t in tasks])
