"""全条件、分布局恢复结果与模型调用账本；低成功率不阻断审计。"""
import sys
from copy import deepcopy
from pathlib import Path
from rc_common import ROOT,SOURCE,METHODS,SHARDS,verify,read,save,sha
from rc_audit import audit_scene,audit_trace
from run import indices


def reject(trace,source,plan,mutate):
    value=deepcopy(trace)
    mutate(value)
    try:
        audit_trace(value,source,plan)
    except (AssertionError,ValueError,KeyError):
        return
    raise AssertionError('Tampering accepted')


def tamper(manifest):
    index=next(i for i in manifest['smoke'] if not manifest['rows'][i]['success'])
    source=manifest['rows'][index]
    plan=read(SOURCE/'plan.json')
    trace=read(ROOT/'tasks'/source['item']['id']/'model/result.json')
    reject(trace,source,plan,lambda v:v.update(success=not v['success']))
    reject(trace,source,plan,lambda v:v.update(training_approved=True))
    reject(trace,source,plan,lambda v:v.update(extra_observations=1))
    reject(trace,source,plan,lambda v:v['attempts'][0].update(result_sha256='0'*64))
    reject(trace,source,plan,lambda v:v['decisions'][0]['event']['request'].update(temperature=1))
    reject(trace,source,plan,lambda v:v['decisions'][0]['event']['response'].update(active_method='sft'))
    return 6


def metrics(rows):
    output={}
    for arm in ('all','original','randomized'):
        group=[r for r in rows if arm=='all' or r['arm']==arm]
        output[arm]={}
        for method in METHODS:
            values=[r['methods'][method] for r in group]
            output[arm][method]=dict(conditions=len(group),success=sum(v['success'] for v in values),
                initially_failed=sum(not r['first_success'] for r in group),
                recovered=sum(not r['first_success'] and r['methods'][method]['success'] for r in group),
                method_attempts=sum(v['attempts'] for v in values),
                new_physical=sum(v['new_physical'] for v in values),
                invalid=sum(v['invalid'] for v in values),calls=sum(len(v['calls']) for v in values))
    return output


def ledger(rows):
    task=[identifier for r in rows for v in r['methods'].values() for identifier in v['calls']]
    startup=[r['request_id'] for r in read(ROOT/'service/ready.json')['replay']]
    assert len(task)==len(set(task)) and len(startup)==2
    assert not set(task)&set(startup)
    disk={p.stem for p in (ROOT/'service/requests').glob('*.json')}
    assert disk==set(task)|set(startup),'Missing or unaccounted model calls'
    assert not list((ROOT/'service').glob('error_*.json'))
    assert len(task)<=22
    return dict(task_calls=len(task),startup_calls=len(startup),unique_requests=len(disk))


def write_report(value):
    lines=['# 三容器随机布局恢复对照','',
        '复用160次已审计首次执行，三方法最多各3次尝试；480条方法轨迹不等于480次独立物理执行。',
        '这是既有开发条件的恢复诊断，不是独立泛化或最终盲测。模型为基础Qwen3.5-4B，无新微调。','',
        '| 布局 | 方法 | 成功/全部 | 恢复/初始失败 | 新物理执行 | 模型调用 |',
        '|---|---|---:|---:|---:|---:|']
    for arm,methods in value['metrics'].items():
        for method,m in methods.items():
            recovered=f"{m['recovered']}/{m['initially_failed']}" if m['initially_failed'] else '不适用'
            lines.append(f"| {arm} | {method} | {m['success']}/{m['conditions']} | {recovered} | {m['new_physical']} | {m['calls']} |")
    lines.extend(['','所有原始失败均保留；同一布局种子用于两个任务，统计单位不是独立的480条轨迹。',
        '参数修正会重置同一布局后重新执行，不是恢复失败瞬间。候选由规则生成；模型收益仅能解释为候选选择贡献。',
        '未额外增加反馈噪声，也未使用OBSERVE；本轮用于分离基础控制恢复与观测策略问题。'])
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main(phase):
    manifest=verify()
    phases=['smoke'] if phase=='smoke' else ['smoke','batch']
    selected=manifest['smoke'] if phase=='smoke' else list(range(160))
    for name in phases:
        for shard in range(SHARDS):
            progress=read(ROOT/'stages'/name/f'{shard}.json')
            assert progress['status']=='completed'
            assert progress['indices']==indices(manifest,name)[shard::SHARDS]
            assert progress['completed']==progress['expected']==len(progress['indices'])
    rows=[]
    for index in selected:
        row=audit_scene(index,manifest)
        assert row==read(ROOT/'tasks'/row['id']/'summary.json')
        rows.append(row)
    checked=ledger(rows)
    value=dict(passed=True,complete=phase=='final',accounted=len(rows),trajectories=len(rows)*3,
        source_initial_executions=len(rows),new_physical=sum(r['new_physical'] for r in rows),
        metrics=metrics(rows),ledger=checked,tamper_checks=tamper(manifest),
        manifest_sha256=sha(ROOT/'manifest.json'),test_used=False,training_approved=False,rows=rows)
    assert value['new_physical']<=66
    save(ROOT/('gate_smoke.json' if phase=='smoke' else 'verification.json'),value)
    if phase=='final':
        write_report(value)
    print(value['metrics'],flush=True)


if __name__=='__main__':
    assert sys.argv[1] in ('smoke','final')
    main(sys.argv[1])
