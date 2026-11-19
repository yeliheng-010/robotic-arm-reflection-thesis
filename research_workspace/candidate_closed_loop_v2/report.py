"""全分母、跨方法物理/噪声配对及4B推理双日志审计。"""
import argparse
import importlib.util
from collections import Counter
from common import ROOT,PARENT,METHODS,read,save,verify,sha,is_smoke
from audit_task import audit


def helper(folder,name):
    spec=importlib.util.spec_from_file_location(folder+'_'+name,PARENT/folder/f'{name}.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(entries):
    rows,results=[] ,[]
    for entry in entries:
        path=ROOT/'tasks'/entry['uid']
        if not (path/'summary.json').exists():
            continue
        row=read(path/'summary.json')
        assert row['uid']==entry['uid'] and row['method']==entry['method']
        assert row['executed']==entry['eligible'] and not row['test_used']
        if row['executed']:
            result=read(path/'result.json')
            checked=audit(result,entry)
            assert row['audit']==checked and row['result_sha256']==sha(path/'result.json')
            assert row['success']==result['success'] and row['status']==result['status']
            assert row['first_success']==result['attempts'][0]['success']
            assert all(row[k]==v for k,v in checked.items() if k!='passed')
            results.append(result)
        else:
            assert row['status']=='skipped_ineligible' and not (path/'result.json').exists()
        rows.append(dict(row,batch=entry['batch'],scene_id=entry['item']['scene_id'],
                         seed=entry['item']['seed'],source=entry['item']['source'],
                         factor=entry['item']['factor'],noise_index=entry['item']['noise_index']))
    return rows,results


def metrics(rows):
    output=[]
    for field in ('all','batch','factor','source','noise_index'):
        values=['all'] if field=='all' else sorted({r[field] for r in rows})
        for value in values:
            for method in METHODS:
                group=[r for r in rows if r['method']==method and (field=='all' or r[field]==value)]
                active=[r for r in group if r['executed']]
                successes=sum(bool(r['success']) for r in active)
                first=sum(bool(r['first_success']) for r in active)
                output.append(dict(field=field,value=value,method=method,accounted=len(group),
                    executed=len(active),skipped=len(group)-len(active),successes=successes,
                    first_success=first,recovered=successes-first,
                    **{k:sum(r.get(k,0) for r in group) for k in
                       ('attempts','calls','invalid','service_errors','call_elapsed_s')}))
    return output


def paired(rows):
    scenes=sorted({r['scene_id'] for r in rows})
    output={}
    for left,right in (('base','tuned'),('rule','base'),('rule','tuned')):
        counts=Counter()
        for scene in scenes:
            group={r['method']:r for r in rows if r['scene_id']==scene}
            if set(group)!=set(METHODS) or not group[left]['executed']:
                counts['unpaired_or_skipped']+=1
                continue
            a,b=group[left]['success'],group[right]['success']
            counts['both_success' if a and b else 'left_only' if a else 'right_only' if b else 'both_fail']+=1
        output[left+'_vs_'+right]=dict(counts)
    return output


def write_report(value):
    lines=['# 4B候选选择器物理闭环','',
           f"处理{value['accounted']}/{value['expected']}，执行{value['executed']}，跳过{value['skipped']}。",
           '| 方法 | 成功/执行 | 首次成功 | 失败后恢复 | 尝试 | 非法选择 | 服务错误 |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for r in value['metrics']:
        if r['field']=='all':
            lines.append(f"| {r['method']} | {r['successes']}/{r['executed']} | {r['first_success']} | "
                         f"{r['recovered']} | {r['attempts']} | {r['invalid']} | {r['service_errors']} |")
    lines += ['','60个开发条件共享6个批次内种子组；不是最终盲测。每组最多3次尝试，未使用最终测试。',
              'base/tuned为同一4B基础权重，只切换adapter；Flash不属于本轮三组主对照。']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main(phase):
    manifest=verify()
    entries=[e for e in manifest['entries'] if phase=='final' or is_smoke(e)]
    rows,results=load(entries)
    old=helper('route_loop_v1','verify')
    comparison=helper('route_loop_v1','compare')
    noisy=helper('noisy_loop_v1','verify')
    value=dict(passed=True,complete=len(rows)==len(entries),expected=len(entries),accounted=len(rows),
               executed=len(results),skipped=len(rows)-len(results),rows=rows,metrics=metrics(rows),
               paired=paired(rows),paired_initials=old.paired_initials(results),
               **comparison.compare_physics(results),**noisy.paired_methods(results),
               candidate_checks=old.candidate_checks(results),test_used=False,training_approved=0,
               manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/('smoke_verification.json' if phase=='smoke' else 'verification.json'),value)
    assert value['complete'],'Incomplete experiment'
    assert not any(r['service_errors'] for r in rows),'Service failure'
    if phase=='smoke':
        for shard in range(3):
            assert read(ROOT/'stages/smoke'/f'shard_{shard}/progress.json')['status']=='completed'
        from tamper import run
        run(entries)
        save(ROOT/'gate_smoke.json',dict(status='ready',manifest_sha256=value['manifest_sha256']))
    else:
        write_report(value)
    print({k:v for k,v in value.items() if k not in ('rows','metrics')})


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
            save(ROOT/'stop_service.json',dict(reason='Final audit finished; release this task service'))
