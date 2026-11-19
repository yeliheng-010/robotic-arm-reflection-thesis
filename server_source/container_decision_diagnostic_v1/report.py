"""动作覆盖是事后诊断上界，不是可部署策略成功率。"""
from cd_common import ROOT, VARIANTS, save


def metrics(manifest, rows, model):
    cases = [case_metrics(case,rows,model) for case in manifest['cases']]
    return dict(cases=cases,old_menu_recoverable=sum(bool(c['original_success_actions']) for c in cases),
        expert_extension_recoverable=sum(bool(c['expert_success_actions']) for c in cases),
        model_variants={v:sum(c['decisions'][v] for c in cases) for v in VARIANTS})


def case_metrics(case, rows, model):
    group = [r for r in rows if r['case_id']==case['id']]
    successful = [r for r in group if r['outcome']['success']]
    available = {r['action_id'] for r in successful if r['origin']=='original_menu'}
    decisions = {}
    for variant in VARIANTS:
        value = next(r['result'] for r in model['rows'] if r['task']['id']==case['id']+'__'+variant)
        decisions[variant] = bool(value['valid'] and value['action']['id'] in available)
    return dict(id=case['id'],initial_error=case['source']['error_type'],
        original_success_actions=sorted(available),
        expert_success_actions=[r['action_id'] for r in successful if r['origin']=='expert_extension'],
        rule_success=case['rule_final']['success'],model_original_success=case['model_final']['success'],
        decisions=decisions)


def write(manifest, rows, model):
    value = metrics(manifest,rows,model)
    save(ROOT/'analysis.json',value)
    lines = ['# 容器随机布局：候选选择与动作覆盖诊断','',
        '覆盖全部11个既有失败案例。先冻结44次模型决策，再执行73个物理分支。',
        '每个分支从原布局/种子重置；一次第三尝试，不恢复失败瞬间。模型为基础4B，adapter禁用。',
        '这是事后开发诊断，不能视作新独立测试，也不能将穷举候选的上界当作可部署策略成功率。','',
        f"- 原候选空间至少一个动作成功：{value['old_menu_recoverable']}/11",
        f"- 降低抬升高度至少一个动作成功：{value['expert_extension_recoverable']}/2（专家扩展）",'',
        '| 模型输入 | 所选动作实际成功/11 |','|---|---:|']
    lines += [f"| {v} | {value['model_variants'][v]}/11 |" for v in VARIANTS]
    lines += ['','expert_hint额外给出规则启发式指导，不能称为无指导模型能力。',
        'reverse仅改变候选及合法ID顺序；summary仅追加已发生历史与失败阶段提醒。',
        'invalid计为未成功，无规则代选；物理失败保留于完整分母。','',
        '| 案例 | 初始错误 | 原候选可恢复动作数 | 低抬升可恢复动作数 |',
        '|---|---|---:|---:|']
    lines += [f"| {c['id']} | {c['initial_error']} | {len(c['original_success_actions'])} | {len(c['expert_success_actions'])} |" for c in value['cases']]
    lines += ['','后续应先根据失败阶段改进候选或选择器，再用新种子进行冻结对照；本轮不训练、不使用最终盲测。']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return value
