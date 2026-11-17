"""Produce a human-readable report and standard static scientific plots."""
import json
import sys
from pathlib import Path
from common import ROOT, read, write, timestamp


def ratio(a, b):
    return f'{a / b:.2f}x' if b else 'n/a'


def main():
    d = read(ROOT / 'analysis/results.json')
    a = read(ROOT / 'analysis/audit.json')
    assert a['passed'] and d['completed'] == 48
    g2, g4 = d['metrics']['G2'], d['metrics']['G4']
    e = d['primary_effect']
    effect = e['task_mean_difference'] * 100
    ci = [x * 100 for x in e['task_bootstrap_95']]
    fci = [x * 100 for x in e['family_bootstrap_95']]
    if effect > 0:
        headline = '在本次固定任务集和相同资源上限下，Check包提高了端到端完整成功率。'
    elif effect < 0:
        headline = '在本次固定任务集和相同资源上限下，Check包的端到端完整成功率更低。'
    else:
        headline = '在本次固定任务集和相同资源上限下，Check包未提高平均端到端完整成功率。'
    rows = []
    def line(s=''):
        rows.append(s)
    line('Prompt2Scene-Check 正式48次实验分析')
    line('生成时间：' + timestamp())
    line()
    line('结论')
    line(headline)
    line(f"G2完整成功{g2['complete_success']}/24；G4完整成功{g4['complete_success']}/24；差值{effect:+.2f}个百分点。")
    line(f'按12个任务整题重采样的探索性95%区间：[{ci[0]:+.2f}, {ci[1]:+.2f}]个百分点。')
    line(f"任务级对照：改善{e['improved_tasks']}题，持平{e['unchanged_tasks']}题，变差{e['worse_tasks']}题。")
    line(f"G4在首次编辑失败的{g4['initial_edit_failed']}次中，有{g4['self_repaired']}次最终场景修复成功；G2为{g2['self_repaired']}/{g2['initial_edit_failed']}。此处按实际场景计数，尚须结合有效finish判断完整成功。")
    line()
    line('设计与冻结')
    line('12题（M01–M06会议室、W01–W06仓库）×2组×2重复；每组固定24个计划单元。每个任务的两组使用相同初始实际状态、公开要求、基础工具和资源上限；G4额外加载Check指南、只读诊断及状态版本提醒。')
    line('seed为1、2；24个配对区块按预存顺序串行运行，G2先和G4先各12个区块。48次为API重复，统计单位为12个任务。')
    line('冻结第二轮开发验证版本；245个文件与5个Unity脚本/项目配置文件记录哈希。正式调度只增加seed/stage参数和独立场景命名空间，Agent循环及评分行为保持不变。')
    line('采用冻结的无自动重试传输策略；未知费用请求会保留预留并停止继续消费。本次实际终止情况见下表及原始日志。')
    line('正式批次预算上限15元；每运行请求16次、工具40次、编辑4批、对象写入100次、输入96000 token、输出12000 token、时间1200秒。请求15、16仅能提交finish。')
    line()
    line('总体计数（每组分母24）')
    labels = [('完整任务成功', 'complete_success'), ('最终场景成功', 'state_success'), ('正常提交finish', 'normal_finish'),
              ('声明complete', 'complete_claims'), ('错误声明complete', 'false_complete'), ('无有效finish报告', 'no_report'),
              ('首次编辑达标', 'first_edit_success'), ('首次编辑失败', 'initial_edit_failed'), ('首次失败后场景自修复', 'self_repaired'),
              ('最终保护违规', 'final_protection_violation'), ('过程保护违规', 'process_protection_violation')]
    for label, key in labels:
        line(f'{label}: G2 {g2[key]}/24；G4 {g4[key]}/24')
    line(f"G4每个编辑版本均执行检查与比较：{g4['flow_adherence']}/24；同时满足先check再compare的顺序：{g4['ordered_flow']}/24。")
    line(f"G4诊断覆盖不完整且由预算/资源停止的运行：{g4['flow_gap_budget_stop']}；诊断覆盖不完整但正常finish的运行：{g4['flow_gap_valid_finish']}。前者不能直接解释为模型自愿忽略流程。")
    line('错误完成声明只针对status=complete且最终状态未达标；无报告单列。二者必须一起解读。保护违规为0只表示本样本未观测到违规，不能估计新增保护收益。')
    line()
    line('终止原因')
    for group in ['G2', 'G4']:
        line(group + ': ' + json.dumps(d['metrics'][group]['stop_reasons'], ensure_ascii=False))
    line('input_budget_precheck表示继续请求的保守输入上界加已用token将超过96000，因此在调用前停止；不是API报错，也不表示实际已超额。该运行的主指标仍按未正常finish记失败。')
    line('明确技术失败：' + (', '.join(d['technical_failure_cells']) or '无'))
    if d['technical_failure_cells']:
        for run_id in d['technical_failure_cells']:
            r = next(r for r in read(ROOT / 'formal/summary.json')['results'] if r['run_id'] == run_id)
            failure = read(ROOT / 'formal' / run_id / 'transport_failure.json')
            line(f"{run_id}：第{r['stats']['requests']}次请求中断，最终场景达标={r['state_success']}，有效finish={r['normal_finish']}；{failure['message']}")
        line('技术失败原运行没有重试或替换；保留分段汇总与日志后，按同一冻结Agent循环继续原定未运行单元。未知请求的费用最高预留额持续保留。技术故障分组不平衡时，应结合以下敏感性结果解读。')
        ss = d['infrastructure_sensitivity']
        line(f"补充敏感性分析：整对剔除受到技术故障影响的配对区块后，G2 {ss['G2']['success']}/{ss['G2']['denominator']}，G4 {ss['G4']['success']}/{ss['G4']['denominator']}。主结果仍为每组24次。")
    line()
    line('逐任务（每组每题2次）')
    for t in d['tasks']:
        line(f"{t['task_id']}: G2 {t['G2']['success']}/2；G4 {t['G4']['success']}/2；差值{100*t['success_difference']:+.0f}个百分点；场景自修复 G2 {t['G2']['repairs']}，G4 {t['G4']['repairs']}")
    line()
    line('六类任务汇总（每类每组4次）')
    family_names = {'M_layout': '整组搬迁', 'M_dynamic_facing': '桌椅布局与动态朝向',
                    'M_permissions': '混合字段权限', 'W_packing': '混合尺寸装架',
                    'W_support': '多层分配与支撑', 'W_rotation_footprint': '朝向与占地联动'}
    for f in d['families']:
        line(f"{family_names[f['family']]} ({','.join(f['tasks'])}): G2 {f['G2']}/4；G4 {f['G4']}/4")
    line('24个配对运行的描述性对照：' + json.dumps(d['paired_run_outcomes'], ensure_ascii=False))
    line()
    line('失败规则类别（每个运行同类最多计一次，可同时属于多类）')
    for phase, name in [('initial', '首次有效编辑后'), ('final', '最终状态')]:
        for group in ['G2', 'G4']:
            line(name + ' ' + group + ': ' + json.dumps(d['failure_categories'][phase][group], ensure_ascii=False))
    line('没有有效编辑的运行，首次阶段使用初始状态分类；首次编辑成功数不把无编辑计作成功。')
    line()
    line('机制示例（说明过程，不替代总体统计）')
    summary = read(ROOT / 'formal/summary.json')
    complete_ids = {r['run_id'] for r in summary['results'] if r['group'] == 'G4' and r['complete_success']}
    example = next((r for r in d['repairs'] if r['run_id'] in complete_ids), None)
    if example:
        line('按运行顺序的首个G4完整成功自修复案例：' + example['run_id'])
        line('首次失败规则：' + ', '.join(example['failed_first']))
        line('工具链：' + ' -> '.join(example['tools']))
        line('该运行在反馈后修改场景，最终独立评分全部通过且正常提交finish；完整逐步动作见对应trace.ndjson。')
    failed = next((r for r in summary['results'] if r['group'] == 'G4' and not r['complete_success']), None)
    if failed:
        grade = read(ROOT / 'formal' / failed['run_id'] / 'offline_final_score.json')
        line('按运行顺序的首个G4失败案例：' + failed['run_id'] + '，终止原因' + failed['stop_reason'])
        line('最终仍失败的规则：' + (', '.join(c['rule_id'] for c in grade['checks'] if not c['passed']) or '无；失败来自未正常终止或报告/资源要求'))
        line('该案例说明收到诊断反馈之后仍可能修复不足，或无法在资源限额内完成收尾。')
    line()
    line('资源与开销（全部计划运行，包含失败运行）')
    for group, m in [('G2', g2), ('G4', g4)]:
        s = m['stats']
        line(f"{group}: 请求{s['requests']}，工具{s['tools']}，编辑{s['edit_batches']}批，已知输入{s['input_tokens']} token，已知输出{s['output_tokens']} token，已知usage估算费用{s['cost_cny']:.6f}元，未知请求另保留最高{m['uncertain_reserved_upper_cny']:.6f}元，平均任务执行{m['mean_seconds']:.2f}秒，中位数{m['median_seconds']:.2f}秒；工具错误{m['tool_errors']}次，已记录超上限{m['caps_exceeded']}次。")
    line('G4/G2比值：请求' + ratio(g4['stats']['requests'], g2['stats']['requests']) + '，输入token' + ratio(g4['stats']['input_tokens'], g2['stats']['input_tokens']) + '，平均执行时间' + ratio(g4['mean_seconds'], g2['mean_seconds']) + '，估算费用' + ratio(g4['stats']['cost_cny'], g2['stats']['cost_cny']))
    line(f"已知usage估算费用{d['cost_estimate_cny']:.6f}元；加上未知请求的完整预留后，账本占用上界{d['cost_with_unknown_reservations_upper_cny']:.6f}元。按冻结单价输入0.8元/百万token、输出2.7元/百万token计算，未计缓存优惠；没有账户账单，因此不称实际扣费。费用和token比值使用已知usage，未知请求的实际用量不可得。")
    line('任务执行时间为Agent的模型与工具循环，包含所有尝试；不包括重置、截图和保存。失败时长不能称为成功完成时间。')
    line(f"计时核查：原harness使用time.monotonic()。有{len(a['timestamp_gap_over_five_seconds'])}个运行的文件时间戳跨度比记录时长多5秒以上，原因未核实；因此不把记录时长直接解释为真实墙钟速度。首请求文件至final_state文件的平均时间戳跨度：G2 {g2['mean_evidence_timestamp_span_seconds']:.2f}秒，G4 {g4['mean_evidence_timestamp_span_seconds']:.2f}秒；这是补充描述，包含末尾状态读取且不含重置/截图。逐运行数值已保存至CSV。")
    if d['technical_failure_cells']:
        ss = d['infrastructure_sensitivity']
        line(f"网络故障等待会影响耗时均值。剔除受技术故障影响的整对区块后，平均执行时间G2 {ss['G2']['mean_seconds']:.2f}秒，G4 {ss['G4']['mean_seconds']:.2f}秒，比值{ratio(ss['G4']['mean_seconds'], ss['G2']['mean_seconds'])}。原始全样本耗时比不能直接解释为Check自身的速度收益或开销。")
    line()
    line('完整性核验')
    line(f"48个计划单元全部有结果；{a['ledger']['requests']}个请求中{a['ledger']['completed_requests']}个有完整响应与usage，{a['ledger']['unknown_requests']}个保留未知费用预留，全部属于formal。所有冻结文件哈希一致。所有最终和中间状态经独立评分复算一致，所有已调用诊断按对应版本回放一致。")
    disagreements = sum(not c['online_offline_final_agree'] for c in a['cells'])
    line(f'在线与独立最终判定不一致：{disagreements}个运行。每题四个运行的初始实际状态相同；模型请求的seed、采样参数和各组提示上下文均与预设条件一致。')
    line(f"原两轮证据保持原样：第二轮{a['round2_preservation']['checked']}个文件、第一轮{a['round1_preservation']['checked']}个文件及{a['round1_scene_preservation']['checked']}个旧场景/元数据文件哈希验证通过。Unity已恢复原场景。")
    line()
    line('解释边界')
    line('这项对照估计的是Check整包（指南、诊断工具、朝向反馈、流程提醒）在同一限额下的作用，无法拆出单一组件的因果贡献。检查结果较长带来的上下文开销也属于本版本的实际端到端表现。')
    line('任务为12个固定题，六个任务族结构相关；每题只有两次重复。探索性区间按整题10000次bootstrap，不能当成48个独立样本或任意Unity任务的总体结论。')
    line(f'补充按六个整任务族重采样的95%区间：[{fci[0]:+.2f}, {fci[1]:+.2f}]个百分点；仅6族，区间也不稳定。没有进行人类参与者实验。')
    line('正式结果全部保留；未因效果方向更改题目、阈值或提示，未把开发运行或研究者预检修正计作正式修复。后续修改需建立新版本，保留本批次，并对受影响的两组按相同范围复验。')
    line()
    line('后续工程建议（本批次未修改，属于对日志的解释）')
    line('优先缩短诊断返回：继续全量执行规则检查，返回失败项的必要测量及通过项摘要；减少重复全场景快照对历史上下文的占用。需在新版本验证信息完整性。')
    line('在剩余输入token不足前预留finish空间，并把剩余token/时间提供给Agent。当前资源提醒仅列请求、工具、编辑和写入余额，输入预算预检可能直接结束循环，尚无提前切换finish的机制。')
    line('这些改动能否提升完整成功率仍需新实验验证。本报告没有以删除预算失败或仅统计已完成报告的方式替代主结果。')
    line()
    line('文件索引（相对于本报告所在目录）')
    for s in ['analysis/results.json：分组、任务、任务族、bootstrap、失败类别及真实修复记录',
              'analysis/runs.csv：48次逐运行可分析数据', 'analysis/audit.json：逐运行与旧证据完整性核验',
              'analysis/overview.png、analysis/task_success.png：标准静态图表',
              'formal/analysis_plan.json、formal/schedule.json、formal/frozen_configuration.json：运行前冻结',
              'formal/summary.json：全部正式运行结果', 'formal/{任务}_{组}_r{重复}/：请求、响应、trace、状态、评分和两张最终截图',
              'Unity_Check_Formal48_Scenes.unitypackage：48次的96个实际初始/最终场景及所需脚本',
              'cost_ledger.ndjson、transport/：费用预留/完成记录及原始响应']:
        line(s)
    (ROOT / 'RESULTS.txt').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    # Analysis-only plotting dependencies live outside the frozen experiment runtime.
    sys.path.insert(0, '/tmp/p2sc-formal-plotdeps')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    colors = ['#697887', '#156f83']
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    names = ['Complete\nsuccess', 'Final state\nsuccess', 'False complete\nclaim', 'No valid\nreport']
    keys = ['complete_success', 'state_success', 'false_complete', 'no_report']
    x = np.arange(len(names))
    for i, (group, m) in enumerate([('G2', g2), ('G4', g4)]):
        bars = axes[0].bar(x + (i - .5) * .36, [m[k] for k in keys], .36, label=group, color=colors[i])
        axes[0].bar_label(bars, padding=3, fmt='%d')
    axes[0].set(xticks=x, xticklabels=names, ylim=(0, 27), ylabel='Runs (24 planned per condition)', title='Formal outcomes, including failures')
    axes[0].legend(frameon=False)
    ratios = [g4['stats']['requests'] / g2['stats']['requests'], g4['stats']['input_tokens'] / g2['stats']['input_tokens'],
              g4['stats']['output_tokens'] / g2['stats']['output_tokens'], g4['stats']['cost_cny'] / g2['stats']['cost_cny']]
    bars = axes[1].bar(['Requests', 'Input tokens', 'Output tokens', 'Est. cost'], ratios, color=colors[1], width=.55)
    axes[1].bar_label(bars, labels=[f'{v:.2f}x' for v in ratios], padding=4)
    axes[1].axhline(1, color=colors[0], linestyle='--', linewidth=1)
    axes[1].set(ylabel='G4 / G2 (recorded usage)', title='Recorded resource overhead', ylim=(0, max(ratios) * 1.2))
    fig.suptitle(f'Frozen Check package: {effect:+.1f} pp complete-success difference | 12 tasks, 2 repeats', fontsize=13)
    if a['ledger']['unknown_requests']:
        fig.supxlabel('Token and cost ratios use known usage; disconnected-request reservation is reported separately.', fontsize=9)
    fig.savefig(ROOT / 'analysis/overview.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 4.6), constrained_layout=True)
    x = np.arange(12)
    for i, group in enumerate(['G2', 'G4']):
        bars = ax.bar(x + (i - .5) * .36, [t[group]['success'] for t in d['tasks']], .36, color=colors[i], label=group)
        ax.bar_label(bars, padding=2, fmt='%d')
    ax.set(xticks=x, xticklabels=[t['task_id'] for t in d['tasks']], ylim=(0, 2.5), yticks=[0, 1, 2], ylabel='Complete successes / 2 repeats', title='Formal task results: fixed tasks, identical caps')
    ax.axvline(5.5, color='#cccccc', linewidth=1)
    ax.legend(frameon=False)
    fig.savefig(ROOT / 'analysis/task_success.png', dpi=180)
    plt.close(fig)
    write(ROOT / 'analysis/plot_provenance.json', dict(time=timestamp(), matplotlib_version=matplotlib.__version__, data='analysis/results.json', analysis_only=True))
    print('Report and two figures created')


if __name__ == '__main__':
    main()
