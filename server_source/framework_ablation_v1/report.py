"""分别报告主实验与预算敏感性，保留全部分母和配对结果。"""
import argparse
from collections import Counter
from itertools import combinations
from common import ROOT,METHODS,read,save,verify,sha,in_phase
from audit_task import audit
from comparison import paired_physics,budget_prefixes


def load(entries):
    rows,pairs=[],[]
    for e in entries:
        folder=ROOT/'tasks'/e['uid']
        if not (folder/'summary.json').exists():
            continue
        r=read(folder/'summary.json')
        assert (r['uid'],r['method'],r['max_attempts'])==(e['uid'],e['method'],e['max_attempts'])
        assert r['executed']==e['eligible'] and not r['test_used'] and not r['training_approved']
        if r['executed']:
            result=read(folder/'result.json')
            checked=audit(result,e)
            assert r['audit']==checked and r['result_sha256']==sha(folder/'result.json')
            assert (r['success'],r['status'])==(result['success'],result['status'])
            assert r['first_success']==result['attempts'][0]['success']
            assert all(r[k]==v for k,v in checked.items() if k!='passed')
            expected_time=sum(d.get('event',{}).get('elapsed_s',0) for d in result['decisions'])
            assert r['call_elapsed_s']==expected_time
            pairs.append((e,result))
        else:
            assert r['status']=='skipped_ineligible' and not (folder/'result.json').exists()
        rows.append(dict(r,batch=e['batch'],scene_id=e['item']['scene_id'],seed=e['item']['seed'],
                         factor=e['item']['factor'],source=e['item']['source'],noise_index=e['item']['noise_index']))
    return rows,pairs


def metrics(rows):
    output=[]
    for budget in (3,4):
        for field in ('all','batch','factor','source','noise_index','seed'):
            values=['all'] if field=='all' else sorted({r[field] for r in rows})
            for value in values:
                for method in METHODS:
                    group=[r for r in rows if r['max_attempts']==budget and r['method']==method
                           and (field=='all' or r[field]==value)]
                    active=[r for r in group if r['executed']]
                    successes=sum(bool(r['success']) for r in active)
                    first=sum(bool(r['first_success']) for r in active)
                    output.append(dict(budget=budget,field=field,value=value,method=method,
                        accounted=len(group),executed=len(active),skipped=len(group)-len(active),
                        successes=successes,first_success=first,recovered=successes-first,
                        initially_failed=len(active)-first,
                        **{k:sum(r.get(k,0) for r in group) for k in
                           ('attempts','calls','invalid','service_errors','call_elapsed_s','elapsed_s')}))
    return output


def paired(rows):
    output={}
    for budget in (3,4):
        selected=[r for r in rows if r['max_attempts']==budget]
        for left,right in combinations(METHODS,2):
            counts=Counter()
            for scene in sorted({r['scene_id'] for r in selected}):
                group={r['method']:r for r in selected if r['scene_id']==scene}
                if set(group)!=set(METHODS) or not group[left]['executed']:
                    counts['unpaired_or_skipped']+=1
                    continue
                a,b=group[left]['success'],group[right]['success']
                counts['both_success' if a and b else 'left_only' if a else 'right_only' if b else 'both_fail']+=1
            output[f'b{budget}_{left}_vs_{right}']=dict(counts)
    return output


def write_report(value,phase):
    lines=['# 四组框架消融与预算对照','',
           f"阶段：{phase}；完成 {value['accounted']}/{value['expected']}；审计通过：{value['passed']}。",'',
           '| 执行预算 | 方法 | 成功/执行 | 失败后恢复/首次失败 | 总执行次数 | 模型调用 | 非法/服务错误 |',
           '|---|---|---:|---:|---:|---:|---:|']
    for r in value['metrics']:
        if r['field']=='all' and r['accounted']:
            lines.append(f"| {r['budget']} | {r['method']} | {r['successes']}/{r['executed']} | "
                         f"{r['recovered']}/{r['initially_failed']} | {r['attempts']} | "
                         f"{r['calls']} | {r['invalid']}/{r['service_errors']} |")
    lines+=['','retry保持参数重复执行；rule使用无历史候选与规则；current仅当前反馈；history额外读取历史。',
            '两模型组均为基础4B，adapter禁用；启动时adapter回放只是服务身份检查，不计为方法任务。',
            '预算3是主实验，预算4是独立敏感性分析；不可合并成一个成功率。',
            '60开发条件共享6个批次内种子组；非独立60种子，非最终盲测，未用于本轮训练。',
            '阶段与接触信息仍为理想信息，XY残差保持原噪声/缺失；结论限定仿真有限候选决策。',
            '各反馈组共用不读取历史的候选；当前状态与尝试编号仍可见。旧版成功率不可直接混合。',
            '恢复时间中的模型调用耗时包含服务排队，仅作运行成本记录，不作严格延迟基准。','',
            '## 配对成功差异','']
    lines.extend(f'- {key}: {counts}' for key,counts in value['paired'].items() if counts)
    lines+=['','## 审计',f"- 同状态配对：{value['physics']}",f"- 预算前缀：{value['budget_prefixes']}",
            '- 逐条件、类型、噪声和种子指标见 verification JSON；不因成功率低而停止或删除样本。']
    (ROOT/f'{phase.upper()}_REPORT.md').write_text('\n'.join(lines)+'\n')
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main(phase):
    manifest=verify()
    entries=[e for e in manifest['entries'] if phase=='final' or in_phase(e,phase)]
    rows,pairs=load(entries)
    value=dict(passed=False,complete=len(rows)==len(entries),expected=len(entries),accounted=len(rows),
               metrics=metrics(rows),paired=paired(rows),rows=rows,physics=paired_physics(pairs),
               budget_prefixes=budget_prefixes(pairs) if phase=='final' else {},
               manifest_sha256=sha(ROOT/'manifest.json'),test_used=False,training_approved=0)
    path=ROOT/('verification.json' if phase=='final' else phase+'_verification.json')
    save(path,value)
    assert value['complete'],'Incomplete experiment'
    assert not any(r['service_errors'] for r in rows),'Service failure'
    stage={'smoke':'smoke','primary':'batch3','final':'batch4'}[phase]
    for shard in range(3):
        assert read(ROOT/'stages'/stage/f'shard_{shard}/progress.json')['status']=='completed'
    if phase=='smoke':
        from tamper import run
        value['tamper_checks']=run(entries)
    value['passed']=True
    save(path,value)
    write_report(value,phase)
    if phase in ('smoke','primary'):
        save(ROOT/f'gate_{phase}.json',dict(status='ready',manifest_sha256=value['manifest_sha256']))
    print({k:v for k,v in value.items() if k not in ('rows','metrics','paired')},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['smoke','primary','final'])
    phase=parser.parse_args().phase
    try:
        main(phase)
    except BaseException as error:
        save(ROOT/(phase+'_audit_failure.json'),dict(passed=False,error=repr(error)))
        raise
