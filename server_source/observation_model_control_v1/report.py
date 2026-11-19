"""逐条件物理审计后生成四组全部预算曲线。"""
import argparse
from om_common import ROOT,verify,read,save,sha,SMOKE_SEEDS,SHARDS,METHODS
from om_audit import audit_scene
from om_metrics import analyze
from om_tamper import check


def render(summary):
    lines=['# 观测处理与选择器四组对照','',
        f"完成{summary['accounted']}/{summary['expected']}条件，{summary['trajectories']}方法轨迹。",
        f"唯一物理执行{summary['physical_executions']}，任务模型调用{summary['model_calls']}，非法{summary['invalid']}。",'',
        '| 预算 | rule_latest | rule_median | base_latest | base_median |','|---|---|---|---|---|']
    for c in summary['budget_analysis']['curves']:
        values=[f"{c['methods'][m]['successes']}/{c['methods'][m]['executed']}" for m in METHODS]
        lines.append('| '+str(c['budget'])+' | '+' | '.join(values)+' |')
    lines+=['','完整六配对、每种子、尝试/观测/token/延迟见BUDGET_CURVES.json（冒烟阶段为smoke_curves.json）。',
        '各预算截取同一轨迹，不是独立实验；这些是既有开发条件，不是新盲测。',
        '两聚合组采集三次测量，只有有效反馈提供给选择器。所有任务调用基础4B，adapter禁用。',
        '服务启动的旧模型参考回放单列，不计为任务结果或新训练。',
        '失败与初始成功均保留；规则旧轨迹复现、同状态物理与同聚合菜单一致性经核验。',
        '未训练、最终测试未用。模型不优于规则时不作模型收益声明。']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main(phase):
    manifest=verify()
    scenes=[s for s in manifest['scenes'] if phase=='final' or s['seed'] in SMOKE_SEEDS]
    stage='batch' if phase=='final' else 'smoke'
    for i in range(SHARDS):
        assert read(ROOT/'stages'/stage/f'shard_{i}/progress.json')['status']=='completed'
    values,rows=[],[]
    for scene in scenes:
        directory=ROOT/'tasks'/scene['id']
        value=read(directory/'result.json')
        assert value['scene']==scene
        audited=audit_scene(value)
        assert audited==read(directory/'summary.json')
        values.append(value)
        rows.append(audited)
    summary=dict(passed=True,complete=True,expected=len(scenes),accounted=len(rows),
        eligible=sum(r['eligible'] for r in rows),rows=rows,budget_analysis=analyze(values,read),
        tamper=check(values),manifest_sha256=sha(ROOT/'manifest.json'),test_used=False,training_approved=False)
    for key in ('trajectories','physical_executions','model_calls','extra_observations','invalid'):
        summary[key]=sum(r[key] for r in rows)
    assert summary['physical_executions']<=len(scenes)*10 and summary['model_calls']<=len(scenes)*4
    summary['startup_replay_calls']=len(read(ROOT/'service/ready.json')['replay'])
    save(ROOT/('verification.json' if phase=='final' else 'smoke_verification.json'),summary)
    save(ROOT/('BUDGET_CURVES.json' if phase=='final' else 'smoke_curves.json'),summary['budget_analysis'])
    if phase=='smoke':
        save(ROOT/'gate_smoke.json',dict(passed=True,manifest_sha256=summary['manifest_sha256']))
    render(summary)
    print({k:v for k,v in summary.items() if k not in ('rows','budget_analysis')},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['smoke','final'])
    args=parser.parse_args()
    try:
        main(args.phase)
    except BaseException as error:
        save(ROOT/f'{args.phase}_audit_failure.json',dict(passed=False,error=repr(error)))
        raise
