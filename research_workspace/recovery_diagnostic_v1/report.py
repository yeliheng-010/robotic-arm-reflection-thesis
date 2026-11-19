"""分别报告预算和缺测诊断，原三次预算分母保持不变。"""
import argparse
import importlib.util
from collections import Counter
from common import ROOT,PARENT,PREVIOUS,METHODS,read,save,verify,sha,is_smoke
from audit_task import audit


def helper(folder,name):
    spec=importlib.util.spec_from_file_location(folder+'_'+name,PARENT/folder/f'{name}.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(entries):
    rows,results=[],[]
    for entry in entries:
        folder=ROOT/'tasks'/entry['uid']
        if not (folder/'summary.json').exists():
            continue
        row=read(folder/'summary.json')
        assert row['uid']==entry['uid'] and row['method']==entry['method']
        assert row['variant']==entry['variant'] and row['max_attempts']==entry['max_attempts']
        assert row['executed'] and not row['test_used'] and not row['training_approved']
        result=read(folder/'result.json')
        checked=audit(result,entry)
        assert row['audit']==checked and row['result_sha256']==sha(folder/'result.json')
        assert row['success']==result['success'] and row['status']==result['status']
        assert row['first_success']==result['attempts'][0]['success']
        assert all(row[k]==v for k,v in checked.items() if k!='passed')
        rows.append(dict(row,scene_id=entry['item']['scene_id']))
        results.append(result)
    return rows,results


def metrics(rows):
    output=[]
    for variant in ('budget4','no_missing'):
        for method in METHODS:
            group=[r for r in rows if r['variant']==variant and r['method']==method]
            pairs=Counter()
            for row in group:
                a,b=row['baseline_success'],row['success']
                pairs['both_success' if a and b else 'baseline_only' if a else 'diagnostic_only' if b else 'both_fail']+=1
            output.append(dict(variant=variant,method=method,tasks=len(group),
                baseline_successes=sum(r['baseline_success'] for r in group),
                success_at_three=sum(r['success_at_three'] for r in group),
                successes=sum(r['success'] for r in group),paired_to_baseline=dict(pairs),
                **{k:sum(r[k] for r in group) for k in
                   ('attempts','calls','invalid','service_errors','prefix_checks','noise_delta_checks','masks_removed')}))
    return output


def physical_checks(results,entries):
    comparison=helper('route_loop_v1','compare')
    old=helper('route_loop_v1','verify')
    noisy=helper('noisy_loop_v1','verify')
    sources={e['source_uid'] for e in entries}
    baselines=[read(PREVIOUS/'tasks'/uid/'result.json') for uid in sorted(sources)]
    value=dict(paired_initials=old.paired_initials(results+baselines),
               **comparison.compare_physics(results+baselines),variants={})
    for name in ('budget4','no_missing'):
        subset=[r for r,e in zip(results,entries) if e['variant']==name]
        value['variants'][name]=noisy.paired_methods(subset)
    return value


def write_report(value):
    lines=['# 预算与反馈缺失诊断','',
        f"完成{value['accounted']}/{value['expected']}方法任务。", '',
        '| 诊断 | 方法 | 原3次成功 | 本轮3次内成功 | 本轮最终成功 | 尝试 | 非法/服务错误 |',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in value['metrics']:
        n=r['tasks']
        lines.append(f"| {r['variant']} | {r['method']} | {r['baseline_successes']}/{n} | "
            f"{r['success_at_three']}/{n} | {r['successes']}/{n} | {r['attempts']} | {r['invalid']}/{r['service_errors']} |")
    lines += ['', 'budget4保持原反馈与前三次轨迹；no_missing保持最多3次和原数值噪声，仅取消缺失。',
        '额外预算或更完整测量下的成功不计入原60条件三次预算成功率。四条件为已知开发失败，非最终盲测。',
        '未进行训练、训练数据补采或最终测试；同条件不同方法/干预不算独立随机场景。']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main(phase):
    manifest=verify()
    entries=[e for e in manifest['entries'] if phase=='final' or is_smoke(e)]
    rows,results=load(entries)
    assert len(rows)==len(entries), 'Incomplete diagnostic'
    assert not any(r['service_errors'] for r in rows), 'Service failure'
    assert sum(r['attempts'] for r in rows)<=sum(e['max_attempts'] for e in entries)
    checks=physical_checks(results,entries)
    if phase=='smoke':
        from tamper import run
        run(entries)
    value=dict(passed=True,complete=True,expected=len(entries),accounted=len(rows),rows=rows,
        metrics=metrics(rows),physical_checks=checks,physical_attempts=sum(r['attempts'] for r in rows),
        test_used=False,training_approved=False,manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/('smoke_verification.json' if phase=='smoke' else 'verification.json'),value)
    if phase=='smoke':
        save(ROOT/'gate_smoke.json',dict(status='ready',manifest_sha256=value['manifest_sha256']))
    else:
        write_report(value)
    print({k:v for k,v in value.items() if k not in ('rows','metrics')},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['smoke','final'])
    phase=parser.parse_args().phase
    try:
        main(phase)
    except BaseException as error:
        save(ROOT/(phase+'_audit_failure.json'),dict(passed=False,error=repr(error)))
        raise
    finally:
        if phase=='final':
            save(ROOT/'stop_service.json',dict(reason='Diagnostic final audit finished'))
