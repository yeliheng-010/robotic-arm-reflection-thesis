"""审计完整账本；门禁不以模型获胜为条件。"""
import argparse
from am_common import ROOT,read,save,sha,verify,SMOKE_SEEDS,SHARDS,MAX_PHYSICAL,MAX_CALLS
from am_audit import audit_scene
from am_metrics import analyze
from am_tamper import check


def ledger(values):
    ids=[]
    for v in values:
        for p in v['trajectories']:
            t=read(p)
            ids.extend(c['event']['response']['id'] for d in t['decisions'] for c in d['choices'] if 'event' in c)
    startup=read(ROOT/'service/ready.json')['replay']
    startup_ids=[r['request_id'] for r in startup]
    assert len(startup_ids)==2 and len(ids)==len(set(ids))
    assert not set(ids)&set(startup_ids)
    assert {p.stem for p in (ROOT/'service/requests').glob('*.json')}==set(ids+startup_ids)
    return dict(task_calls=len(ids),startup_calls=len(startup_ids),all_calls=len(ids)+len(startup_ids))


def render(summary):
    lines=['# 主动观测与相关历史：四方法对照','',
        f"完成{summary['accounted']}/{summary['expected']}条件，{summary['trajectories']}轨迹，{summary['physical_executions']}次唯一物理执行。",'',
        '| 方法 | 三次执行内成功 | 实际执行 | 额外观测 | 模型调用 | 非法输出 |','|---|---|---|---|---|---|']
    for m,v in summary['analysis']['overall']['methods'].items():
        lines.append(f"| {m} | {v['success']}/{v['executed']} | {v['attempts']} | {v['extra_observations']} | {v['model_calls']} | {v['invalid']} |")
    lines+=['','实际累计1/2/3次成功见ANALYSIS.json；模型看见剩余执行预算，前缀不等价于重新设定预算的实验。',
        '6个种子组的开发对照，非最终测试；全部跳过、失败、零收益与不利结果保留。',
        '传感器为合成快照重采样，理想错误类型/阶段仍由执行器给出。候选是规则生成，非端到端策略。',
        '基础4B显式关闭adapter；两模型仅历史输入不同，历史不参与候选生成或当前残差补偿。',
        '无训练；启动回放调用单计。工程审计通过不代表模型优势或统计显著。']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main(phase):
    manifest=verify()
    scenes=[s for s in manifest['scenes'] if phase=='final' or s['seed'] in SMOKE_SEEDS]
    stage='batch' if phase=='final' else 'smoke'
    for i in range(SHARDS):
        assert read(ROOT/'stages'/stage/f'shard_{i}/progress.json')['status']=='completed'
    values,rows=[],[]
    for s in scenes:
        p=ROOT/'tasks'/s['id']
        v=read(p/'result.json')
        assert v['scene']==s
        r=audit_scene(v)
        assert r==read(p/'summary.json')
        values.append(v)
        rows.append(r)
    summary=dict(passed=True,complete=True,expected=len(scenes),accounted=len(rows),
        eligible=sum(r['eligible'] for r in rows),rows=rows,analysis=analyze(values,read),
        tamper=check(values),ledger=ledger(values),manifest_sha256=sha(ROOT/'manifest.json'),
        test_used=False,training_approved=False)
    for k in ('trajectories','physical_executions','extra_observations','model_calls','invalid'):
        summary[k]=sum(r[k] for r in rows)
    assert summary['physical_executions']<=len(scenes)*MAX_PHYSICAL
    assert summary['model_calls']==summary['ledger']['task_calls']<=len(scenes)*2*MAX_CALLS
    save(ROOT/('verification.json' if phase=='final' else 'smoke_verification.json'),summary)
    save(ROOT/('ANALYSIS.json' if phase=='final' else 'smoke_analysis.json'),summary['analysis'])
    if phase=='smoke':
        save(ROOT/'gate_smoke.json',dict(passed=True,manifest_sha256=summary['manifest_sha256']))
    render(summary)
    print({k:v for k,v in summary.items() if k not in ('rows','analysis')},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['smoke','final'])
    args=parser.parse_args()
    try:
        main(args.phase)
    except BaseException as error:
        save(ROOT/f'{args.phase}_audit_failure.json',dict(passed=False,error=repr(error)))
        raise
