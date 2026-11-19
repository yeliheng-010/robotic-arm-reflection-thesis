"""复算全部已完成任务；部分完成与通过审计分别报告。"""
import importlib.util
import json
from pathlib import Path
import sys
from noisyloop.design import ROOT,ARMS
from noisyloop.protocol import verify
from noisyloop.audit import audit
from semanticfix2.protocol import sha
from stability.collection_status import atomic


def load_previous(name):
    path=ROOT.parent/'route_loop_v1'/f'{name}.py'
    spec=importlib.util.spec_from_file_location('frozen_'+name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_item(item):
    directory=ROOT/'tasks'/item['id']
    result=json.loads((directory/'result.json').read_text())
    row=json.loads((directory/'summary.json').read_text())
    assert row['audit']==audit(result,item)
    for key in ('id','arm','seed','factor','pair_id','noise_index','noise_repeat','noise_profile'):
        assert row[key]==item[key]
    assert row['success']==result['success'] and row['status']==result['status']
    for key,value in row['audit'].items():
        if key!='passed':
            assert row[key]==value
    return result,dict(row,result_sha256=sha(directory/'result.json'))


def metrics(rows):
    output=[]
    for profile in range(6):
        for arm in ARMS:
            group=[r for r in rows if r['noise_index']==profile and r['arm']==arm]
            output.append(dict(noise_index=profile,arm=arm,expected=12,completed=len(group),
                **{key:sum(r[key] for r in group) for key in
                   ('success','attempts','calls','invalid','service_errors','noise_projections')}))
    return output


def exposure(results):
    fields=[entry for result in results for step in result['attempts']
            for entry in step['noise_audit'].values()]
    return dict(eligible_fields=len(fields),missing_fields=sum(f['missing'] for f in fields),
        changed_visible_fields=sum(not f['missing'] and any(x!=0 for x in f['delta']) for f in fields),
        note='Only XY residuals corrupted; stage/contact geometry remain ideal')


def paired_methods(results):
    known,checks,diverged={},0,0
    for result in results:
        for index,decision in enumerate(result['decisions']):
            key=(result['item']['pair_id'],decision['after_attempt'])
            step=result['attempts'][index]
            if key not in known:
                known[key]=(decision,step)
                continue
            other,prior_step=known[key]
            if other['before']==decision['before']:
                assert prior_step['projection_seed']==step['projection_seed']
                assert prior_step['noise_audit']==step['noise_audit']
                assert other['feedback']==decision['feedback']
                assert other['candidates']==decision['candidates']
                checks+=1
            else:
                diverged+=1
    return dict(paired_candidate_sets=checks,diverged_inputs=diverged)


def write_report(summary):
    lines=['# 第一批噪声闭环状态','',
        f"已完成 {summary['completed']}/{summary['expected']}；已完成部分审计通过。",
        '开发条件6个；任务数包含噪声配置、随机实现与两种方法，不等于独立场景或训练样本。',
        '', '| 噪声配置 | 方法 | 已完成/计划 | 成功 | 尝试 | 模型调用 | 非法 | 服务错误 |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for row in summary['metrics']:
        lines.append(f"| {row['noise_index']} | {row['arm']} | {row['completed']}/{row['expected']} | "
            f"{row['success']} | {row['attempts']} | {row['calls']} | {row['invalid']} | {row['service_errors']} |")
    observed=summary['exposure']
    lines.extend(['',f"可扰动字段 {observed['eligible_fields']}，实际缺失 {observed['missing_fields']}，"
        f"可见数值发生改变 {observed['changed_visible_fields']}。",
        '仅扰动XY残差；错误阶段与接触几何保持理想。原始值和噪声审计不进入模型输入。',
        f"成功紧邻转移 {summary['successful_transitions']}；训练批准0。规则与混合来源分别保留。",
        '底层复用引擎的context仍为route_loop_v1；本实验身份以外层item和冻结协议为准。'])
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main():
    protocol=verify()
    pairs=[read_item(i) for i in protocol['items'] if (ROOT/'tasks'/i['id']/'summary.json').exists()]
    results,rows=[p[0] for p in pairs],[p[1] for p in pairs]
    old,comparison=load_previous('verify'),load_previous('compare')
    transitions=old.transition_rows(results)
    summary=dict(passed=True,complete=len(rows)==len(protocol['items']),expected=len(protocol['items']),
        completed=len(rows),metrics=metrics(rows),rows=rows,exposure=exposure(results),
        paired_initials=old.paired_initials(results),candidate_checks=old.candidate_checks(results),
        **comparison.compare_physics(results),**paired_methods(results),
        successful_transitions=len(transitions),training_approved=0,test_used=False,
        protocol_sha256=sha(ROOT/'protocol.json'))
    atomic(ROOT/'verification.json',summary)
    atomic(ROOT/'transitions.json',dict(rows=transitions,training_approved=0))
    write_report(summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='rows'}))


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        atomic(ROOT/'verification_failure.json',dict(passed=False,error=repr(error)))
        raise
