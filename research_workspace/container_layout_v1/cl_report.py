"""从原始执行与坐标重算结果，包含全部预登记条件。"""
import copy
import sys
from collections import Counter
from cl_common import read, save, verify, sha
from cl_design import ROOT, SHARDS, ARMS
from cl_run import indices
from cl_worker import audit_row


def rejects(row, plan, mutate):
    altered=copy.deepcopy(row)
    mutate(altered)
    try:
        audit_row(altered,plan)
    except (AssertionError, KeyError, ValueError):
        return
    raise AssertionError('Tampering was accepted')


def tamper_checks(row, plan):
    rejects(row,plan,lambda r:r.update(success=not r['success']))
    rejects(row,plan,lambda r:r['step'].update(result_sha256='0'*64))
    rejects(row,plan,lambda r:r.update(training_approved=True))
    rejects(row,plan,lambda r:r['geometry']['positions']['BlueBin'].__setitem__(0,-1.))


def statistics(rows):
    output={}
    for arm in ARMS:
        selected=[r for r in rows if r['item']['arm']==arm]
        executed=[r for r in selected if r['status']=='executed']
        output[arm]=dict(planned=len(selected),executed=len(executed),
            success=sum(r['success'] is True for r in executed),
            geometry_rejected=len(selected)-len(executed),
            failures=dict(Counter(r['error_type'] for r in executed if not r['success'])))
    pairs={}
    for r in rows:
        key=(r['item']['seed'],r['item']['source'])
        pairs.setdefault(key,{})[r['item']['arm']]=r['success'] is True
    paired=Counter('both_success' if a['original'] and a['randomized'] else
        'original_only' if a['original'] else 'randomized_only' if a['randomized'] else
        'both_fail' for a in pairs.values())
    return dict(arms=output,paired=dict(paired))


def markdown(report):
    lines=['# 三容器随机布局资格实验','',
        '这是无故障单次执行资格评估，不是模型/反思改进实验，也不是训练数据验收。', '',
        '| 布局 | 计划条件 | 实际执行 | 成功 | 几何拒绝 |',
        '|---|---:|---:|---:|---:|']
    for arm,row in report['metrics']['arms'].items():
        lines.append(f"| {arm} | {row['planned']} | {row['executed']} | {row['success']} | {row['geometry_rejected']} |")
    lines.extend(['','40个布局种子，每种布局复用两个任务；原布局重复不能当作80种不同几何场景。',
        '所有失败保留。需结合失败类型决定下一轮可达性/控制器修复，不自动按成功筛选训练数据。',
        '没有新增微调，没有使用最终盲测。','',
        '## 首个预登记种子的前后画面',''])
    for row in report['rows'][:4]:
        lines.append('### '+row['item']['id'])
        lines.append('')
        for image in row.get('images',{}):
            if image.endswith('before.png'):
                from pathlib import Path
                lines.extend([f"![原始仿真初态]({Path(image).relative_to(ROOT).as_posix()})",''])
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main(phase):
    plan=verify()
    phases=['smoke'] if phase=='smoke' else ['smoke','batch']
    expected=indices(plan,'smoke') if phase=='smoke' else list(range(len(plan['items'])))
    for name in phases:
        for shard in range(SHARDS):
            state=read(ROOT/'stages'/name/f'{shard}.json')
            assert state['status']=='completed'
            assert state['indices']==indices(plan,name)[shard::SHARDS]
            assert state['completed']==state['expected']==len(state['indices'])
    rows=[]
    for index in expected:
        item=plan['items'][index]
        row=read(ROOT/'runs'/item['id']/'result.json')
        assert row['index']==index
        assert read(ROOT/'runs'/item['id']/'summary.json')==dict(passed=True,**row)
        audit_row(row,plan)
        rows.append(row)
    representative=next(r for r in rows if r['status']=='executed')
    tamper_checks(representative,plan)
    report=dict(passed=True,complete=phase=='final',accounted=len(rows),
        manifest_sha256=sha(ROOT/'manifest.json'),metrics=statistics(rows),
        physical_executions=sum(r['step'] is not None for r in rows),
        tamper_checks=4,training_approved=False,test_used=False,rows=rows)
    save(ROOT/('gate_smoke.json' if phase=='smoke' else 'verification.json'),report)
    if phase=='final':
        markdown(report)
    print(report['metrics'])


if __name__=='__main__':
    assert sys.argv[1] in ('smoke','final')
    main(sys.argv[1])
