"""开发收益与新种子验证分开，保留负结果和几何特权信息边界。"""
from cm_common import ROOT, METHODS, save


def metrics(rows):
    return dict(conditions=len(rows),success={m:sum(r['success'][m] for r in rows) for m in METHODS},
        gains=[r['id'] for r in rows if r['success']['geometry'] and not r['success']['rule']],
        regressions=[r['id'] for r in rows if r['success']['rule'] and not r['success']['geometry']],
        new_physical=sum(r['new_physical'] for r in rows),
        activated=sum(r['motion']['geometry']['active'] for r in rows),
        fallback=sum(r['motion']['geometry']['fallback'] is not None for r in rows))


def write(value, *, stage):
    m = value['metrics']
    title = '旧失败开发对照' if stage=='development' else '新种子验证'
    lines = [f'# 世界坐标姿态与路径检查：{title}','',
        '几何专家使用完整仿真状态，不应声称为纯视觉或纯模型的自主能力。',
        '两方法最多3次尝试；共享相同的前两次执行，仅第三次允许几何姿态适配。','',
        '| 方法 | 成功/条件 |','|---|---:|',
        f"| 原规则 | {m['success']['rule']}/{m['conditions']} |",
        f"| 几何动作适配 | {m['success']['geometry']}/{m['conditions']} |",'',
        f"新增恢复：{len(m['gains'])}；退化：{len(m['regressions'])}；新增物理执行：{m['new_physical']}。",
        f"检查器触发{m['activated']}例，其中无静态可行候选、显式回退原规则{m['fallback']}例。",'',
        '新增恢复ID：'+', '.join(m['gains']), '退化ID：'+', '.join(m['regressions']), '',
        '候选只改变抓取姿态，保持抓取坐标、参数、布局及噪声不变。原姿态和8个世界竖直姿态按固定顺序检查。',
        '路径覆盖预抓取、接近、抓取、抬升、运输和下降，每段51个离散样本；夹爪自由刚体随法兰同步。',
        '静态检查保持夹爪初始开合状态，不预测被抓物体运动或动态跟踪误差，不检查释放后回程。',
        '接触排除源物体、目标容器和支撑面，沿用原监控定义；实际物理成功仍由完整执行判定。',
        '没有训练、没有模型调用、没有使用最终盲测。新验证40个种子各含两个相关任务，不能当作80个独立布局。']
    if stage=='development':
        lines += ['',f"进入新种子验证：{value['promote']}。门槛是新增恢复至少1例且原成功案例无退化。"]
    (ROOT/('DEVELOPMENT_REPORT.md' if stage=='development' else 'REPORT.md')).write_text('\n'.join(lines)+'\n')
    save(ROOT/(stage+'_metrics.json'),m)
