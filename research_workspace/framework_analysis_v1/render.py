"""只输出记录支持的观察；把后续设计与已完成实验区分。"""
def write_report(root,value,cases):
    lines=['# 框架历史消融：只读归因','',
        f"重新审计 {value['reaudited_tasks']} 任务；{value['source_files_unchanged']} 个来源文件hash未变。",
        '新物理执行0，新模型调用0，新训练输入0，最终测试未读取。','',
        '| 预算 | 配对决策 | 非空历史位置 | 相同当前输入 | 相同输入同选 | 相同输入异选 |',
        '|---|---:|---:|---:|---:|---:|']
    for b,c in value['comparison_totals'].items():
        lines.append(f"| {b} | {c.get('paired_positions',0)} | {c.get('nonempty_history_positions',0)} | "
            f"{c.get('same_current_input',0)} | {c.get('same_input_same_choice',0)} | {c.get('same_input_different_choice',0)} |")
    lines+=['','## 预算4的历史组：信息与决策结构','']
    c=value['features']['b4_history']
    for key,val in c.items():
        lines.append(f'- {key}: {val}')
    lines+=['','## 对解释的约束','',
        '首个失败后的决策历史必为空；只有后续决策可检验历史贡献。两个预算共享前缀，不相加当独立证据。',
        'measured_option表示规则已利用可见残差计算具体候选，不保证物理成功；stage_specific为候选结构描述，不是正确答案标签。',
        '规则一致性是在模型实际遇到的状态上重算，不代表完整规则轨迹与模型轨迹相同。',
        '当前参数/姿态可携带既往修正信息；删除显式历史不等于移除全部过去行为的影响。',
        '有历史读入但输出相同，不能证明模型没读历史，也不能证明所有任务都不需要历史。',
        'exact observable matches只搜索预算4历史组的89或实际决策数；未找到不同历史同输入不代表理论上不存在。','',
        '## 失败及规则独胜条件','']
    for c in cases['failures']:
        terminal=c['methods']['history']['attempts'][-1]
        lines.append(f"- b{c['budget']} {c['scene']}: rule_only={c['rule_only_success']}; "
                     f"terminal={terminal['error']}/{terminal['phase']}; residuals={terminal['residuals']}")
    lines+=['','详细决策特征见decisions.json，逐条件轨迹与分歧见cases.json；下一阶段设计另见NEXT_PLAN.md。']
    (root/'REPORT.md').write_text('\n'.join(lines)+'\n')
