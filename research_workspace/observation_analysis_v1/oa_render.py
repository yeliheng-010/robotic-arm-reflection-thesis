"""输出全条件测量诊断，不只保留成功案例。"""
def render(root,summary,rows):
    stats=summary['statistics']
    lines=['# 观测聚合只读归因','',
        f"重新审计{len(rows)}条件，来源{summary['source_files_unchanged']}文件hash不变。",
        f"实际消费字段误差方向：{stats['error_directions']}；配对结果不同条件{len(stats['different_outcome_conditions'])}。",'',
        '| 条件 | 初始阶段 | 实际消费字段 | 最后测量离群 | latest/median误差(mm) | 误差方向 | 预算2/3配对 |',
        '|---|---|---|---|---|---|---|']
    for row in rows:
        initial=row['initial']
        if initial is None:
            lines.append(f"| {row['id']} | 无修正决策 | — | — | — | — | 初始成功或未执行，详见cases.json |")
            continue
        used=set(initial['consumed_fields'].values())-{None}
        for metric in initial['fields']:
            if metric['field'] not in used:
                continue
            errors=metric['errors_m']
            pairs='/'.join(b['paired'] for b in row['budgets'] if b['budget']>1)
            lines.append(f"| {row['id']} | {row['outcomes']['latest'][0]['phase']} | {metric['field']} | "
                f"{metric['last_sample_outlier']} | {errors['latest']*1000:.3f}/{errors['median']*1000:.3f} | "
                f"{metric['error_direction']} | {pairs} |")
    lines+=['','原阶段启发式未标记但动作消费了测量的条件：',str(stats['heuristic_misses']),'',
        '实际消费表示selected.kind及facts.measurement引用此字段，不证明该字段是物理故障的正确归因。',
        '原exposure/协议不改；本报告是补充的事后诊断，包含误差变大、无收益和失败。',
        '候选参数和ID可能随观测变化，不能说两方法候选菜单完全一致。',
        'cases.json保留三次可见测量、审计真值、有效测量、候选类型、完整选定动作和后续执行链。',
        '审计真值/离群标记只用于离线分析，不可进入未来模型输入。',
        '无新增物理执行、模型调用、训练或最终测试。']
    (root/'REPORT.md').write_text('\n'.join(lines)+'\n')
