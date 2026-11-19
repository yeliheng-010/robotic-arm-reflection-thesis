"""报告完整预算曲线，不选择有利预算或隐去失败条件。"""
def write_report(root,value):
    curves=value['budget_analysis']
    lines=['# 独立种子观测聚合验证','',
        f"完成{value['accounted']}/{value['expected']}条件；资格通过{value['eligible']}；"
        f"物理执行{value['physical_executions']}/{value['physical_budget']}。",
        f"独立种子组{curves['independent_seed_groups']}；方法latest/median；模型调用0。",'',
        '| 预算 | latest成功/执行 | median成功/执行 | latest/median物理尝试 | latest/median额外观测 | latest独胜/median独胜 |',
        '|---|---:|---:|---:|---:|---:|']
    for c in curves['curves']:
        a,b=(c['methods'][m] for m in ('latest','median'))
        lines.append(f"| {c['budget']} | {a['successes']}/{a['executed']} | {b['successes']}/{b['executed']} | "
            f"{a['attempts']}/{b['attempts']} | {a['extra_observations']}/{b['extra_observations']} | "
            f"{c['paired'].get('latest_only',0)}/{c['paired'].get('median_only',0)} |")
    lines+=['','## 全条件记录','',
        '| 条件 | 资格 | 相关离群出现 | latest/median成功 | latest/median轨迹长度 |',
        '|---|---|---|---|---|']
    for r in value['rows']:
        e=r['exposure']
        lines.append(f"| {r['id']} | {r['qualification']} | {e['related_outlier']>0} | "
                     f"{r['successes']} | {e['trace_lengths']} |")
    lines+=['','预算曲线事前冻结，从最多3次的同一执行轨迹截断，不能相加当三组独立实验。',
        '两方法首次失败均使用同一状态的相同三次合成测量，观测费用一致；状态变化后不复用旧测量。',
        '预算1没有修正决策，因此额外观测计费为0；表中尝试按方法轨迹计费，共享首次执行不在独立物理执行总数中重复计算。',
        '资格跳过与实际执行分开；easy_control、无相关离群、无收益和失败条件均保留。',
        '这是新训练资格种子上的开发验证，非最终盲测；同种子两物体相关，不宣称统计显著。',
        '同状态短窗口中位数为规则聚合，不是模型微调或跨执行长期记忆；原始残差仅用于审计。',
        'BUDGET_CURVES.json提供逐种子/逐条件配对结果；FAILURES.json保留最终失败轨迹。',
        '训练批准0、最终测试未读取，旧pilot结果不并入本轮分母。']
    (root/'REPORT.md').write_text('\n'.join(lines)+'\n')
