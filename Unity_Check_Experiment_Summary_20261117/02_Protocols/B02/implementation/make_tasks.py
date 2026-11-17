"""Translate the delivered task design, then add four disjoint development fixtures."""
import math
from common import ROOT,read,write
from engine import public_task

def o(i,p,s,yaw=0,kind='box'):return dict(id=i,position=p,size=s,yaw=yaw,kind=kind)
def r(i,a,b):return dict(id=i,min=a,max=b)
def direction(p,q):return math.degrees(math.atan2(q[0]-p[0],q[2]-p[2]))%360
def dev(i,objects,allowed,request,regions):
    return dict(id=i,scene='D',initial={v['id']:v for v in objects},allowed=allowed,request=request,regions=regions,keepout=[],inside=[],support=[],facing=[],relative=[],distance=[],markers={},grounded=[],witness={})

def build():
    designs=read(ROOT.parent/'check_protocol_v2/work/task_design.json')['tasks']
    result=[public_task(d) for d in designs]
    a=o('DA',[-3,.3,-2],[.6,.6,.6]);b=o('DB',[-1,.3,-2],[.6,.6,.6]);lock=o('DFixed',[3,.5,0],[.6,1,.6])
    d=dev('D01',[a,b,lock],{'DA':['x','z'],'DB':['x','z']},'只移动 DA、DB 的 x、z，将两箱完整放入开发摆放区并保持落地、互不重叠。所有旋转、尺寸及 DFixed 保持；开发通道留空。',[r('开发摆放区',[-2,-.01,1],[0,1,2.5])])
    d.update(inside=[('DA','开发摆放区'),('DB','开发摆放区')],grounded=['DA','DB'],keepout=[r('开发通道',[.3,0,-2],[1.3,2,3])],witness={'DA':o('DA',[-1.5,.3,1.5],a['size']),'DB':o('DB',[-.5,.3,1.5],b['size'])});result.append(public_task(d))
    a=o('DBoxA',[-3,.2,0],[.7,.4,.5]);b=o('DBoxB',[-2,.35,1],[.5,.7,.7]);s=o('DSupport',[2,1,-1],[2,2,1.6],kind='table')
    d=dev('D02',[a,b,s,lock],{x:['x','y','z'] for x in ['DBoxA','DBoxB']},'将 DBoxA、DBoxB 完整放入开发支撑区，由 DSupport 支撑且互不重叠。原朝向、尺寸、支撑台及其他对象保持，开发通道留空。',[r('开发支撑区',[1,2,-1.8],[3,3.2,-.2])])
    d.update(inside=[(x,'开发支撑区') for x in d['allowed']],support=[(x,'DSupport') for x in d['allowed']],keepout=[r('开发通道',[-.5,0,-3],[.5,3,3])],witness={'DBoxA':o('DBoxA',[1.5,2.2,-1],a['size']),'DBoxB':o('DBoxB',[2.4,2.35,-1],b['size'])});result.append(public_task(d))
    a=o('DChairA',[-2,.5,-1],[.55,1,.55],kind='chair');b=o('DChairB',[1,.5,1],[.55,1,.55],180,'chair');point=[0,.05,3.8]
    d=dev('D03',[a,b,lock],{x:['yaw'] for x in ['DChairA','DChairB']},'DChairA、DChairB 的位置不动，只改 yaw 面向开发标记 DP。水平误差不超过10度。所有其他对象、字段和尺寸保持，不能发生实体穿透。',[])
    d.update(markers={'DP':point},facing=[(x,'DP') for x in d['allowed']],grounded=list(d['allowed']),witness={v['id']:o(v['id'],v['position'],v['size'],direction(v['position'],point),'chair') for v in [a,b]});result.append(public_task(d))
    s=o('DTable',[-3,.75,-2],[1.6,1.5,1],kind='table');a=o('DSeatA',[-4.2,.5,-3],[.55,1,.55],kind='chair');b=o('DSeatB',[-1.8,.5,-3],[.55,1,.55],kind='chair');target=[-1.8,.75,2.5]
    d=dev('D04',[s,a,b,lock],{'DTable':['x','z'],'DSeatA':['x','z','yaw'],'DSeatB':['x','z','yaw']},'将 DTable 完整放入开发桌区；DSeatA、DSeatB 分别完整放入开发座区A、B，面向最终 DTable 桌心。所有对象落地，无实体穿透。DFixed、尺寸和其他字段保持，开发保留区留空。',[r('开发桌区',[-3,-.01,1.5],[-.5,2,3.5]),r('开发座区A',[-3.5,-.01,.2],[-2,1.5,1.7]),r('开发座区B',[-1.8,-.01,.2],[-.3,1.5,1.7])])
    d.update(inside=[('DTable','开发桌区'),('DSeatA','开发座区A'),('DSeatB','开发座区B')],facing=[('DSeatA','DTable'),('DSeatB','DTable')],grounded=list(d['allowed']),keepout=[r('开发保留区',[1,0,-3],[2,3,3])],witness={'DTable':o('DTable',target,s['size'],kind='table')})
    for v,p in [(a,[-2.8,.5,1]),(b,[-.8,.5,1])]:d['witness'][v['id']]=o(v['id'],p,v['size'],direction(p,target),'chair')
    result.append(public_task(d))
    for t in result:write(ROOT/'tasks'/(t['id']+'.json'),t)
    write(ROOT/'task_manifest.json',{'formal':[t['id'] for t in result[:12]],'development':[t['id'] for t in result[12:]],'provenance':'Formal design matches delivered v2. Development fixtures use disjoint IDs, geometry and target regions; no formal model calls.'})
    print('Wrote 12 formal tasks and 4 disjoint development fixtures.')

if __name__=='__main__':build()
