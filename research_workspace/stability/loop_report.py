"""由完整闭环结果生成组会表格与实际仿真截图。"""
import json
from pathlib import Path
from stability.experiment import OUT
from stability.loop_freeze import ROOT
from stability.loop_protocol import ARMS

LABELS = {'retry': '直接重试', 'rule': '规则方法', 'base': '未微调模型', 'adapted': '微调模型'}


def table(result):
    lines = ['| 方法 | 成功任务 | 成功率 | 平均尝试次数 | 无效输出/调用 | 服务错误 |',
             '|---|---:|---:|---:|---:|---:|']
    for arm in ARMS:
        row = result['metrics'][arm]
        invalid = f"{row['invalid']}/{row['calls']}" if row['calls'] else '不适用'
        lines.append(f"| {LABELS[arm]} | {row['successes']}/{row['tasks']} | "
            f"{row['success_rate']:.1%} | {row['mean_attempts']:.2f} | {invalid} | {row['service_errors']} |")
    return lines


def cases(config, result):
    rows = {(r['case'], r['arm']): r for r in result['rows']}
    lines = ['| 场景 | 故障 | retry | rule | base | adapted |', '|---|---|---|---|---|---|']
    for index, task in enumerate(config['tasks']):
        cells = [('成功' if rows[index, arm]['success'] else '失败')+f"（{rows[index, arm]['attempts']}次）" for arm in ARMS]
        lines.append(f"| {index}: {task['source']}→{task['destination']} | {task['fault']} | "+' | '.join(cells)+' |')
    return lines


def comparison_images(config, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    rows = {(r['case'], r['arm']): r for r in result['rows']}
    improved = [i for i in range(len(config['tasks'])) if rows[i, 'adapted']['success'] and not rows[i, 'base']['success']]
    chosen = improved[:1] or [0]
    failures = [i for i in range(len(config['tasks'])) if not rows[i, 'adapted']['success']]
    chosen += failures[:1]
    for index in dict.fromkeys(chosen):
        fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
        for axis, arm in zip(axes, ARMS):
            row = rows[index, arm]
            path = ROOT/'tasks'/f'{index:02d}'/arm/f"attempt_{row['attempts']}"/'after.png'
            axis.imshow(Image.open(path))
            axis.axis('off')
            axis.set_title(f"{arm}: {'success' if row['success'] else 'failure'} / {row['attempts']} attempts")
        task = config['tasks'][index]
        fig.suptitle(f"Case {index}: {task['source']} to {task['destination']} / {task['fault']} / seed {task['seed']}")
        fig.tight_layout()
        fig.savefig(ROOT/f'case_{index:02d}_comparison.png', dpi=150, bbox_inches='tight')
        plt.close(fig)
    return list(dict.fromkeys(chosen))


def main():
    result = json.loads((ROOT/'result.json').read_text())
    config = json.loads((ROOT/'manifest.json').read_text())
    assert result['status'] == 'completed' and result['verification']['passed']
    selected = comparison_images(config, result)
    lines = ['# 微调模型闭环开发评估', '',
        '冻结6个新场景、四种方法，共24次完整执行。相同初始状态、持续故障、最多3次尝试；所有任务保留在分母。', '',
        '这批使用validation任务组的新seed40000，不是最终测试集；两个任务组内的故障结果也不是大量独立场景证据。', '']
    lines += table(result)+['', '## 各场景完整结果', '']+cases(config, result)
    lines += ['', '场景4四组首次均成功，没有触发反思，不计作反思收益。在其余5个首次失败场景中，retry为0/5、rule为5/5、base为2/5、adapted为5/5；完整总表仍保留全部6个场景。', '',
        '## 执行与后处理记录', '',
        'Slurm 3717最终为FAILED：场景4的两组模型首次成功，无模型调用，旧汇总代码却读取不存在的requests.jsonl。线程池等待在途任务结束，24份物理result.json全部完整保留。', '',
        '新增安全汇总函数允许零调用时没有日志，但有调用缺少日志仍拒绝；3项回归测试先2项失败，修复后合并16项测试通过。独立loop_finalize补回两份汇总，再执行全量审计。24份原始轨迹SHA256前后不变，失败日志与恢复代码hash见completion_recovery.json；没有重跑、筛除或改写物理结果。', '',
        '冻结的执行代码按原身份保留以供复核；后续新运行应使用loop_results的安全汇总并建立新的冻结版本，不能直接重复本次一次性入口。']
    lines += ['', '## 解读边界', '',
        '- 平均尝试次数包括失败任务；非法输出可能提前结束，因此次数少不能单独解释为效率更好。',
        '- 无效输出包括解析、参数约束和不改变参数等失败；服务错误另列。模型没有规则回退或JSON修补。',
        '- 基础模型和微调模型共用NF4/FP16权重、非思考提示、greedy、256输出token，只切换adapter。',
        '- 此为小规模同族场景开发对照，不证明统计显著、跨物体、真实视觉或真实机械臂泛化。',
        '- 保留全部失败；截图按首个微调改善案例及首个微调失败案例选取（如存在），不用于替代全量表格。', '',
        '## 实际仿真截图', '']
    lines += [f'![场景{i}四组最终状态](closed_loop_v1/case_{i:02d}_comparison.png)' for i in selected]
    lines += ['', '证据目录：closed_loop_v1，包含manifest/result、全部原始轨迹、前后截图和客户端/服务端请求。']
    text = '\n'.join(lines)+'\n'
    (OUT/'CLOSED_LOOP_REPORT.md').write_text(text)
    (ROOT/'report.md').write_text(text.replace('(closed_loop_v1/', '('))
    print(json.dumps({'report': str(OUT/'CLOSED_LOOP_REPORT.md'), 'images': selected, 'metrics': result['metrics']}))


if __name__ == '__main__':
    main()
