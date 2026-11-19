"""完整分母、实际机制暴露和来源审计；不自动导出训练数据。"""
import argparse
from copy import deepcopy
from pilot import ROOT,SEEDS,SHARDS,verify,read,save,sha,MAX_PHYSICAL
from audit import audit_scene,audit_trace
from exposure import exposure


def tamper(values):
    probes=[]
    for mode in ('occlusion','outlier','side_effect'):
        for value in values:
            if value['scene']['mechanism']!=mode:
                continue
            for path in value['trajectories']:
                trace=read(path)
                if trace['decisions']:
                    probes.append((value,trace))
                    break
            if probes and probes[-1][0] is value:
                break
    rejected=[]
    for value,original in probes:
        q=read(ROOT/'qualification'/value['scene']['id']/'result.json')
        reference=read(q['steps'][0]['result_path'])['records'][0]
        mutations={'physical_hash':lambda t:t['attempts'][0].update(result_sha256='0'*64),
            'observation_state':lambda t:t['decisions'][0]['observation']['samples'][0].update(state={}),
            'visible_truth':lambda t:t['decisions'][0]['feedback']['evidence'].update(hidden_truth=1),
            'budget':lambda t:t.update(extra_observations=99),
            'success':lambda t:t.update(success=not t['success'])}
        for name,mutate in mutations.items():
            changed=deepcopy(original)
            mutate(changed)
            try:
                audit_trace(changed,reference)
            except (AssertionError,ValueError,KeyError):
                rejected.append(dict(mechanism=value['scene']['mechanism'],kind=name))
            else:
                raise AssertionError('Tamper accepted: '+name)
    assert rejected,'No auditable physical decisions in qualification smoke'
    return dict(passed=True,rejections=rejected,count=len(rejected))


def write_report(value):
    lines=['# 12条件机制资格结果','',
        f"完成{value['accounted']}/{value['expected']}；技术合格{value['eligible']}；"
        f"物理执行{value['physical_executions']}/{value['physical_budget']}；额外观测{value['extra_observations']}。",'',
        '| 条件 | 技术合格 | 机制暴露 | 观测到成功路径 | 各轨迹成功 |',
        '|---|---|---|---|---|']
    for r in value['rows']:
        e=r['exposure']
        lines.append(f"| {r['id']} | {r['eligible']} | {e['mechanism_exposed']} | "
                     f"{e['observed_success_path']} | {r['successes']} |")
    lines+=['','A/B最多3次物理执行，C最多4次且有额外资格分支；不得跨机制合并成模型成功率。',
        'B两组首次失败均获得同一状态的三次测量，仅聚合方式不同；不跨执行状态复用历史。',
        '重观测是不可变物理快照的合成测量重采样；不是实时相机采集。原始测量和离群标签仅供审计。',
        'model=null，模型调用0、训练批准0、最终测试未用；技术审计通过不等于机制暴露或方法有效。',
        '无额外观测与重观测的资源差异是显式干预；不得归因于大模型。有限分支未成功不等于无解。']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main(phase):
    manifest=verify()
    scenes=[s for s in manifest['scenes'] if phase=='final' or s['seed']==SEEDS[0]]
    for shard in range(SHARDS):
        stage='smoke' if phase=='smoke' else 'batch'
        assert read(ROOT/'stages'/stage/f'shard_{shard}/progress.json')['status']=='completed'
    values,rows=[],[]
    for scene in scenes:
        path=ROOT/'tasks'/scene['id']
        value=read(path/'result.json')
        assert value['scene']==scene
        checked=audit_scene(value)
        assert checked==read(path/'summary.json')
        values.append(value)
        rows.append(dict(checked,exposure=exposure(value)))
    summary=dict(passed=True,complete=True,expected=len(scenes),accounted=len(rows),
        eligible=sum(r['eligible'] for r in rows),physical_executions=sum(r['physical_executions'] for r in rows),
        physical_budget=sum(MAX_PHYSICAL[s['mechanism']] for s in scenes),
        extra_observations=sum(r['extra_observations'] for r in rows),rows=rows,tamper=tamper(values),
        manifest_sha256=sha(ROOT/'manifest.json'),model_calls=0,training_approved=False,test_used=False)
    assert summary['physical_executions']<=summary['physical_budget']
    save(ROOT/f'{phase}_verification.json',summary)
    if phase=='smoke':
        save(ROOT/'gate_smoke.json',dict(passed=True,manifest_sha256=summary['manifest_sha256']))
    write_report(summary)
    print({k:v for k,v in summary.items() if k!='rows'},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['smoke','final'])
    phase=parser.parse_args().phase
    try:
        main(phase)
    except BaseException as error:
        save(ROOT/f'{phase}_audit_failure.json',dict(passed=False,error=repr(error)))
        raise
