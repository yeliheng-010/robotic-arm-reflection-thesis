"""机制暴露与性能分开报告；不按是否获胜放行。"""
import argparse
from collections import Counter
from ap_common import ROOT,verify,read,save,sha,SMOKE_SEEDS,SHARDS,METHODS,MAX_PHYSICAL
from ap_audit import audit_scene
from ap_metrics import analyze
from ap_tamper import check


def mechanism_summary(details):
    out={}
    for method in METHODS:
        traces=[t for t in details if t['method']==method]
        ds=[d for t in traces for d in t['rows']]
        keys=('missing','conflict','visibility_recovered','later_observation','unresolved')
        out[method]=dict(decisions=len(ds),**{k:sum(d[k] for d in ds) for k in keys},
            phases=dict(Counter(d['phase'] for d in ds)),
            multi_stage_conditions=sum(len({d['phase'] for d in t['rows']})>1 for t in traces))
    return out


def render(summary):
    lines=['# 主动观测预算资格试验','',
        f"完成{summary['accounted']}/{summary['expected']}条件，{summary['trajectories']}规则轨迹；物理执行{summary['physical_executions']}。",'',
        '| 预算 | fixed_first成功 | adaptive成功 | 两者方法尝试 | 两者额外观测 |','|---|---|---|---|---|']
    for c in summary['budget_analysis']['curves']:
        a,b=(c['methods'][m] for m in METHODS)
        lines.append(f"| {c['budget']} | {a['successes']}/{a['executed']} | {b['successes']}/{b['executed']} | "
            f"{a['attempts']}/{b['attempts']} | {a['extra_observations']}/{b['extra_observations']} |")
    lines+=['','机制暴露（决策次数，不是独立条件数）：',str(summary['mechanism_exposure']),'',
        '两策略均最多3次物理尝试、2次额外观测；实际观测费用可不同，全部报告。',
        'fixed_first第一次失败取三次观测；adaptive以可见缺测、少于两次有效测量或>30mm冲突决定补看。',
        '一致性不是校准概率，不代表多数离群已被排除。全部同状态样本取中位数；跨状态不复用。',
        '缺测和离群共同形成压力条件，不宣称从本试验分离两噪声各自的因果作用。',
        '数据用途为train_candidate资格试验，非最终测试；6种子组，不宣称统计显著。',
        '单阶段/复合阶段分项与全部失败见BUDGET_CURVES.json、verification.json和原始tasks。',
        '门禁仅检查工程正确性；是否实际缺测、冲突、再次观测和多阶段故障由结果另报。',
        '本轮没有模型、历史推理或训练，不把规则分配效果称为模型收益。']
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
    analysis=analyze(values,read)
    summary=dict(passed=True,complete=True,expected=len(scenes),accounted=len(rows),eligible=sum(r['eligible'] for r in rows),
        rows=rows,budget_analysis=analysis,tamper=check(values),manifest_sha256=sha(ROOT/'manifest.json'),
        mechanism_exposure=mechanism_summary(analysis['exposure']),test_used=False,training_approved=False,model_calls=0)
    for k in ('trajectories','physical_executions','extra_observations'):
        summary[k]=sum(r[k] for r in rows)
    assert summary['physical_executions']<=len(scenes)*MAX_PHYSICAL
    save(ROOT/('verification.json' if phase=='final' else 'smoke_verification.json'),summary)
    save(ROOT/('BUDGET_CURVES.json' if phase=='final' else 'smoke_curves.json'),analysis)
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
