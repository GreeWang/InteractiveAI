"""Human-readable results and standard static plots from audited formal data."""
import json
import statistics
import sys
from common import ROOT,read,write,timestamp


def main():
    d=read(ROOT/'formal/analysis.json');a=read(ROOT/'audit/results.json');assert a['passed'] and d['completed']==48
    m=d['metrics'];effect=d['primary_effect'];pp=100*effect['task_mean_difference'];ci=[100*x for x in effect['task_bootstrap_95']];fci=[100*x for x in effect['family_bootstrap_95']]
    lines=['Check V3新任务正式48次实验分析','生成时间：'+timestamp(),'',
        f"本次固定任务集的端到端完整成功率：G2 {m['G2']['complete_success']}/24，G4 {m['G4']['complete_success']}/24，差值{pp:+.2f}个百分点。",
        f'以12个任务为单位的10000次整题bootstrap探索性95%区间：[{ci[0]:+.2f}, {ci[1]:+.2f}]个百分点；六任务族重采样补充区间：[{fci[0]:+.2f}, {fci[1]:+.2f}]个百分点。',
        f"逐任务：改善{effect['improved_tasks']}题，持平{effect['unchanged_tasks']}题，变差{effect['worse_tasks']}题。区间仅描述固定小样本，不证明任意Unity场景的总体效果。",'',
        '研究设计与冻结',
        'V3M01–V3M06会议室，V3W01–V3W06仓库；六类各一题中等、一题困难。12个新几何实例在任何本批模型调用前固定，但仍来自先前使用的六种模板，且由研究者在看到先前实验后构建。',
        '12题×G2/G4两组×两次重复，共48次；每组分母固定24。请求携带seed 1、2，不宣称API严格确定性或重复独立抽样。24个配对区块预先随机化，两组先运行各12区块；每题四个运行均重置到相同实际初始状态。',
        'V3 actor循环、预算收尾、精简反馈、判定和独立评分器与已验收开发版逐字节一致。两组共享预算提醒及相同请求、工具、token和时间限额；G4额外加载Check指南、只读诊断及流程提醒。',
        '196个文件以及Unity脚本、项目版本、依赖配置在启动前记录哈希。17项单元检查、12题真实Unity可行解、58个故意错误状态、独立包围盒、保存重开及重置验证通过。预检不是模型运行或模型修复。',
        '主指标同时要求预算内正常提交有效finish及独立最终状态全部达标。status=partial也不自动记失败或成功；以真实状态和正常终止联合判定。未报告、超限、预算停止或技术故障均保留。',
        '模型收到公开合同和结构化实际场景状态，未读取参考解、离线评分或截图；本批不涉及人类参与者操作或视觉输入能力的检验。','',
        '分组指标（每组固定24次）']
    keys=[('完整任务成功','complete_success'),('最终场景达标','state_success'),('正常finish','normal_finish'),('无报告','no_report'),('声明complete','complete_claims'),
          ('错误声明complete','false_complete'),('首次编辑失败','initial_edit_failed'),('首次失败后的场景自修复','self_repaired'),
          ('过程保护违规','process_protection_violation'),('最终保护违规','final_protection_violation'),('提前报告阶段触发','report_phase_entered')]
    for label,k in keys:lines.append(f"{label}：G2 {m['G2'][k]}/24；G4 {m['G4'][k]}/24")
    for g in ['G2','G4']:
        lines.append(f"{g}自修复条件分母：{m[g]['self_repaired']}/{m[g]['initial_edit_failed']}次首次失败；终止原因："+json.dumps(m[g]['stop_reasons'],ensure_ascii=False))
    lines += [f"G4每个编辑版本的检查/比较覆盖：{m['G4']['flow_adherence']}/24；同时符合先check后compare顺序：{m['G4']['ordered_flow']}/24。",
        f"检查/比较覆盖不完整且触发报告阶段：{m['G4']['flow_gap_with_report_phase']}次；覆盖不完整且未触发报告阶段：{m['G4']['flow_gap_without_report_phase']}次。报告阶段禁止额外工具调用，前者不能直接解释成模型自愿忽略流程。",
        '自修复按首次编辑失败到最终场景达标计数，未正常收尾的场景修复另与完整成功区分。零误报需要结合声明complete和无报告数量解读；零保护违规仅表示本样本未观察到违规。','',
        '逐任务完整成功（每题每组2次）']
    design={t['id']:t for t in read(ROOT/'task_design.json')['tasks']}
    for t in d['tasks']:lines.append(f"{t['task_id']} {design[t['task_id']]['difficulty']}：G2 {t['G2']['success']}/2，G4 {t['G4']['success']}/2；状态达标G2 {t['G2']['state_success']}/2，G4 {t['G4']['state_success']}/2；差值{100*t['success_difference']:+.0f}个百分点。")
    names={'meeting_rigid':'整组搬迁','meeting_facing':'桌椅布局与当前朝向','meeting_permissions':'混合字段权限','warehouse_packing':'混合尺寸装架','warehouse_support':'多层分配支撑','warehouse_footprint':'旋转占地与朝向'}
    lines += ['','任务族汇总（每族每组4次）']
    for f in d['families']:lines.append(f"{names[f['family']]} ({','.join(f['tasks'])})：G2 {f['G2']}/4，G4 {f['G4']}/4。")
    lines += ['配对运行描述性计数：'+json.dumps(d['paired_run_outcomes'],ensure_ascii=False),'','失败类别（每个运行同类最多计一次，可同时属于多类）']
    for phase in ['first_edit','final']:
        for g in ['G2','G4']:lines.append(phase+' '+g+'：'+json.dumps(d['failure_categories'][phase][g],ensure_ascii=False))
    lines += ['','真实过程示例（按运行顺序选择，用于解释，不能替代总体统计）']
    summary=read(ROOT/'formal/summary.json');rs=summary['results']
    partial_pass=[r['run_id'] for r in rs if r['complete_success'] and r['finish']['status']!='complete']
    if partial_pass:lines.append('按运行前主指标，以下运行虽未自称complete，但正常结束且独立终态全部通过，仍计完整成功：'+', '.join(partial_pass))
    good=next((r for r in rs if r['group']=='G4' and r['complete_success'] and r['self_repaired']),None)
    bad=next((r for r in rs if r['group']=='G4' and not r['complete_success']),None)
    for r in [good,bad]:
        if r is None:continue
        f=ROOT/'formal'/r['run_id'];trace=[json.loads(x) for x in (f/'trace.ndjson').read_text().splitlines()] if (f/'trace.ndjson').exists() else []
        grade=read(f/'offline_final_score.json')
        lines.append(r['run_id']+'：工具链 '+ ' -> '.join(e.get('tool','invalid') for e in trace))
        lines.append('最终失败规则：'+(', '.join(c['rule_id'] for c in grade['checks'] if not c['passed']) or '无'))
        if (f/'offline_edit_01.json').exists():lines.append('首次失败规则：'+', '.join(c['rule_id'] for c in read(f/'offline_edit_01.json')['checks'] if not c['passed']))
        lines.append('原始finish状态：'+(r['finish']['status'] if r['finish'] else 'no_report'))
        if not r['complete_success']:
            contract=read(ROOT/'tasks'/(r['task_id']+'.json'))['contract'];current={o['id']:o for o in read(f/'final_state.json')['objects']};reference={o['id']:o for o in read(ROOT/'preflight'/r['task_id']/'reference_state.json')['objects']}
            for row in grade['checks']:
                if row['passed'] or not row['rule_id'].startswith('nonoverlap:'):continue
                pair=set(row['rule_id'].split(':')[1:])
                support=next(((box,table) for box,table in contract['support'] if {box,table}==pair),None)
                if support:
                    box,table=support;bottom=current[box]['bounds_min'][1];top=current[table]['bounds_max'][1]
                    lines.append(f'支撑接触核查：{box}实际底面Y={bottom:.8f}，{table}顶面Y={top:.8f}，差值{bottom-top:+.8f}米；同题预检可行解的箱底Y={reference[box]["bounds_min"][1]:.8f}，全部规则通过。因此存在无穿透的可行接触状态。')
                    if r['finish'] and 'conflict' in json.dumps(r['finish']).lower():lines.append('该例模型报告将问题解释为规则冲突；实际可行解已反驳这一全局无解解释。报告格式和partial状态有效，不代表失败解释正确。')
                    break
    lines += ['所有12题实际预检可行解均通过，因此模型自述“任务无解/规则矛盾”需要单独核验。报告解释不是评分真值；支撑贴合容差0.01米与非重叠分离轴容差0.001米须同时满足。','',
        '效果解读',
        '本批的收益主要体现在面向当前桌心及混合字段权限场景；六个任务族的具体计数见上表。不能只展示改善的题：V3M02和V3W03的G4成功数低于G2。',
        'G4的13次完整成功中，10次发生在首次编辑失败之后，是真实模型修复链；G2未观测到首次失败后修复成功。初次失败后的分母不同，条件修复比例不能当作随机分配的独立因果效应。',
        '完成声明可靠性与解释可靠性应分开：G4没有错误complete声明，但partial报告仍可能错误归因于“规则冲突”。两组均没有观察到保护违规，因此本批没有新增保护收益的组间证据。','',
        '资源与技术故障']
    for g,v in m.items():
        s=v['stats'];wall=statistics.mean(r['wall_seconds'] for r in rs if r['group']==g)
        lines.append(f"{g}：请求{s['requests']}，工具{s['tools']}，编辑{s['edit_batches']}批，已知输入{s['input_tokens']}、输出{s['output_tokens']} token，usage费用估算{s['cost_cny']:.6f}元；未知请求另预留{v['unknown_reserved_cny']:.6f}元；平均monotonic记录时长{v['mean_seconds']:.2f}秒，平均wall_seconds {wall:.2f}秒；工具错误{v['tool_errors']}次，传输故障{v['technical_failures']}次。")
    def ratio(x,y):return f'{x/y:.2f}倍' if y else '无法计算'
    lines.append('G4/G2已知用量比：输入token '+ratio(m['G4']['stats']['input_tokens'],m['G2']['stats']['input_tokens'])+'；输出token '+ratio(m['G4']['stats']['output_tokens'],m['G2']['stats']['output_tokens'])+'；估算费用 '+ratio(m['G4']['stats']['cost_cny'],m['G2']['stats']['cost_cny']))
    lines.append('记录时长保留原harness口径，并另存wall_seconds；技术等待、休眠或时钟差异的原因没有逐项核实，不把失败时长或原始耗时比直接解释为成功完成速度。')
    lines.append(f"响应截断与格式：G2有{m['G2']['length_limited_responses']}次finish_reason=length、{m['G2']['json_parse_errors']}次JSON解析错误；G4为{m['G4']['length_limited_responses']}次和{m['G4']['json_parse_errors']}次。次数是响应事件，不是独立运行数。")
    lines.append(f"finish字段结构/类型校验失败：G2 {m['G2']['finish_schema_errors']}次，G4 {m['G4']['finish_schema_errors']}次。有效JSON也可能因verified/unresolved/limitations不是字符串列表而被拒绝；重复失败没有由宿主自动改写。")
    lines.append('报告阶段单次输出上限为750 token。若输出未闭合且修正仍重复过长内容，预留机会也可能耗尽；原始请求只明确显示剩余总输出预算，未单独告知本次750上限。此项沟通局限属于本冻结版本，两组均适用，运行中未修改。')
    lines.append('技术故障运行：'+(', '.join(d['technical_failure_cells']) or '无'))
    sens=d['infrastructure_sensitivity'];lines.append(f"补充剔除受技术故障影响的整对区块后：G2 {sens['G2']['success']}/{sens['G2']['denominator']}，G4 {sens['G4']['success']}/{sens['G4']['denominator']}；主分母仍固定24。")
    b=d['billing'];lines += [f"本批{b['requests']}个请求，其中{b['completed']}个有完整响应与usage，{b['unknown']}个未知请求保留全额预留。已知费用估算{b['known_cny']:.6f}元，未知预留{b['unknown_reserved_cny']:.6f}元，本批账本上界{d['local_ledger']['total']:.6f}元，限额15元。",
        f"本地历史账本按request_id保守去重后累计上界{d['global_local_upper']['total']:.6f}元，限额300元。平台扣费及账本外消费不可见；估算沿用冻结单价且不假设缓存优惠。",'',
        '完整性与解释边界',
        '全部48个计划单元的初始实际状态、模型条件、可见预算、精简/全量诊断、最终及中间独立评分、模型自写finish、usage和账本已核对。全部冻结干预文件及原有四批证据哈希保持一致；旧正式与V3开发的Unity资产保持原样；运行结束已恢复原场景。',
        '48次不能当成48个独立任务。任务级bootstrap以整题保留两组和两次重复，任务族重采样为补充；固定手工任务、模板相关性及每题仅两次重复限制推断。',
        '估计的是Check整包效果，包括指南、诊断及流程提醒，不能拆出单一组件贡献。V2正式48次、V3开发8次与本批题目不同，跨批次变化仅作描述，未合并挑选有利运行。没有收集人类参与者结果。','',
        '文件索引',
        'formal/analysis.json：总体、任务、任务族、区间、修复与失败类别；formal/runs.csv：48次逐运行数据。',
        'audit/results.json：独立核验；formal/analysis_plan.json、schedule.json、frozen_configuration.json：运行前冻结。',
        'formal/{题目}_{组}_r{重复}/：实际请求/响应、trace、状态、精简及全量诊断、独立评分、finish和两张最终截图。',
        'TASKS.txt及tasks/：具体要求；preflight/：实际可行解与负例；Unity_Check_V3_Formal_Scenes.unitypackage：96个初始/最终场景。']
    (ROOT/'RESULTS.txt').write_text('\n'.join(lines)+'\n')
    plot(d)
    print('Saved formal report and two static figures')


def plot(d):
    sys.path.insert(0,'/tmp/p2sc-formal-plotdeps')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    (ROOT/'figures').mkdir(exist_ok=True);m=d['metrics'];colors=['#697887','#156f83']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(1,2,figsize=(12,4.6),constrained_layout=True);x=np.arange(4);keys=['complete_success','state_success','false_complete','no_report']
    for i,g in enumerate(['G2','G4']):
        bars=ax[0].bar(x+(i-.5)*.36,[m[g][k] for k in keys],.36,color=colors[i],label=g);ax[0].bar_label(bars,padding=3,fmt='%d')
    ax[0].set(xticks=x,xticklabels=['Complete\nsuccess','Final state\nsuccess','False complete\nclaim','No valid\nreport'],ylim=(0,27),ylabel='Runs (24 planned per condition)',title='V3 formal outcomes');ax[0].legend(frameon=False)
    stats=['requests','input_tokens','output_tokens','cost_cny'];ratios=[m['G4']['stats'][k]/m['G2']['stats'][k] if m['G2']['stats'][k] else 0 for k in stats]
    bars=ax[1].bar(['Requests','Input tokens','Output tokens','Est. cost'],ratios,color=colors[1]);ax[1].bar_label(bars,labels=[f'{v:.2f}x' for v in ratios],padding=3)
    ax[1].axhline(1,color=colors[0],linestyle='--',linewidth=1);ax[1].set(ylim=(0,max([1]+ratios)*1.2),ylabel='Recorded G4 / G2',title='Recorded resource overhead')
    fig.suptitle(f"V3 Check package: {100*d['primary_effect']['task_mean_difference']:+.1f} pp | 12 new task instances, 2 repeats",fontsize=13)
    fig.supxlabel('Token/cost ratios use known usage; unknown reservations and timing are reported separately.',fontsize=9);fig.savefig(ROOT/'figures/overview.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(12,4.5),constrained_layout=True);x=np.arange(12)
    for i,g in enumerate(['G2','G4']):
        bars=ax.bar(x+(i-.5)*.36,[t[g]['success'] for t in d['tasks']],.36,color=colors[i],label=g);ax.bar_label(bars,padding=2,fmt='%d')
    ax.set(xticks=x,xticklabels=[t['task_id'] for t in d['tasks']],ylim=(0,2.5),yticks=[0,1,2],ylabel='Complete successes / 2 repeats',title='Fixed new task results under identical caps');ax.tick_params(axis='x',labelrotation=30);ax.legend(frameon=False)
    fig.savefig(ROOT/'figures/task_success.png',dpi=180);plt.close(fig)
    write(ROOT/'figures/provenance.json',dict(time=timestamp(),matplotlib=matplotlib.__version__,data='formal/analysis.json',analysis_only=True))


if __name__=='__main__':main()
