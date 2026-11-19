"""合并提示诊断和固定快照重试证据，训练保持关闭。"""
import argparse
from od_common import ROOT,read,save,sha,verify,SHARDS,SMOKE_CASES,MAX_PHYSICAL
from od_model_audit import audit as model_audit
from od_physics_audit import audit_case
from od_metrics import analyze
from od_tamper import check


def render(summary):
    lines=['# 观测决策诊断','',f"物理快照完成{summary['accounted']}/{summary['expected']}；唯一执行{summary['physical_executions']}。",'',
        '| 选择器与固定补看数 | 下一次成功 | 实际物理执行 | 逻辑补看费用 |','|---|---|---|---|']
    for name,v in summary['analysis']['overall']['arms'].items():
        lines.append(f"| {name} | {v['successes']}/{v['snapshots']} | {v['executions']} | {v['extra_observations']} |")
    lines+=['','提示诊断（各分母及无效输出保留）：',str(summary['model']['summary']),'',
        '固定原失败快照选择新配置，再按相同场景种子重置执行一次，不是恢复仿真失败瞬间。',
        '补看数固定为0/1/2，两选择器共享同快照噪声前缀；模型的执行选择阶段禁止继续补看但保留真实预算。',
        '明确缺测指令属于专家策略注入，不能当作模型自主理解或学习收益。费用探针检验显式定义的读取，不代表物理决策能力。',
        '来源为旧开发集的全部缺测快照，条件/种子相关，结果不是新独立样本、完整闭环成功率或最终测试。',
        '首次/末尾菜单变体用于检查位置敏感性；所有提示均在结果前冻结，不挑赢家。无训练，无自动标签生成。']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main(phase):
    manifest=verify()
    model=model_audit()
    cases=manifest['cases'] if phase=='final' else manifest['cases'][:SMOKE_CASES]
    stage='batch' if phase=='final' else 'smoke'
    for i in range(SHARDS):
        assert read(ROOT/'stages'/stage/f'shard_{i}/progress.json')['status']=='completed'
    values,rows=[],[]
    for case in cases:
        folder=ROOT/'tasks'/case['case_id']
        value=read(folder/'result.json')
        assert value['case']==case
        row=audit_case(value)
        assert row==read(folder/'summary.json')
        values.append(value)
        rows.append(row)
    summary=dict(passed=True,complete=True,expected=len(cases),accounted=len(rows),model=model,
        physical_executions=sum(r['physical_executions'] for r in rows),branches=sum(r['branches'] for r in rows),
        invalid=sum(r['invalid'] for r in rows),analysis=analyze(values,rows),
        tamper_rejections=check(values),manifest_sha256=sha(ROOT/'manifest.json'),
        test_used=False,training_approved=False)
    assert summary['physical_executions']<=min(MAX_PHYSICAL,len(cases)*6)
    save(ROOT/('verification.json' if phase=='final' else 'smoke_verification.json'),summary)
    save(ROOT/('ANALYSIS.json' if phase=='final' else 'smoke_analysis.json'),summary['analysis'])
    if phase=='smoke':
        save(ROOT/'gate_physics_smoke.json',dict(passed=True,manifest_sha256=summary['manifest_sha256']))
    render(summary)
    print({k:v for k,v in summary.items() if k not in ('analysis','model')},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['smoke','final'])
    args=parser.parse_args()
    try:
        main(args.phase)
    except BaseException as error:
        save(ROOT/f'{args.phase}_audit_failure.json',dict(passed=False,error=repr(error)))
        raise
