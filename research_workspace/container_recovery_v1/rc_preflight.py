"""逐条审计既有初态，冻结全量三方法恢复协议。"""
from collections import Counter
from pathlib import Path
import unittest
from cl_common import verify as parent_verify
from cl_worker import audit_row
from loopstudy.actions import candidates,choose_rule
from rc_common import ROOT,SOURCE,PARENT,METHODS,read,save,sha


def sources():
    plan=parent_verify()
    report=read(SOURCE/'verification.json')
    assert report['passed'] and report['complete'] and report['accounted']==160
    assert len(report['rows'])==160 and report['physical_executions']==160
    for i,row in enumerate(report['rows']):
        assert row['index']==i and row['item']==plan['items'][i]
        assert row['status']=='executed'
        audit_row(row,plan)
    assert sum(not r['success'] for r in report['rows'])==11
    return report['rows']


def smoke_indices(rows):
    selected={next(i for i,r in enumerate(rows) if r['item']['arm']==arm and r['success'])
              for arm in ('original','randomized')}
    for error in ('empty_grasp','ik_failure','collision'):
        selected.add(next(i for i,r in enumerate(rows) if r['error_type']==error))
    return sorted(selected)


def failure_analysis(rows):
    failed=[]
    for source in rows:
        if source['success']:
            continue
        step=source['step']
        evidence=step['feedback']['evidence']
        options=candidates(step['feedback'],step['state'],[],legacy=False)
        failed.append(dict(id=source['item']['id'],error=source['error_type'],
            phase=evidence['motion_context']['phase'],contacts=evidence.get('contacts',[]),
            grasp_residual_xy=evidence.get('grasp_residual_xy'),
            available_grasps=evidence['diagnostics']['available_candidate_count'],
            correction_menu=len(options),kinds=dict(Counter(r['kind'] for r in options)),
            rule_choice=choose_rule(options,step['state'],report=step['feedback'])['kind']))
    save(ROOT/'FAILURE_ANALYSIS.json',dict(rows=failed,recoverability='pending physical execution'))
    lines=['# 初始失败分析','',
        '11个失败全部纳入恢复；4空抓和5碰撞发生在抓取阶段，2个IK失败发生于运输阶段。',
        'IK失败不能依据仍存在的抓取残差判为抓取偏移；本轮先检验原候选空间，不按结果追改规则。',
        '静态几何预检不保证动态路径无碰撞，现有证据不能直接判定不可恢复。','',
        '| 条件 | 错误 | 阶段 | 接触对象 | 修正候选数 |','|---|---|---|---|---:|']
    lines += [f"| {r['id']} | {r['error']} | {r['phase']} | {r['contacts']} | {r['correction_menu']} |" for r in failed]
    (ROOT/'FAILURE_ANALYSIS.md').write_text('\n'.join(lines)+'\n')


def freeze():
    assert not (ROOT/'manifest.json').exists()
    rows=sources()
    failure_analysis(rows)
    suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_policy.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful() and result.testsRun>=8
    identities=dict(read(SOURCE/'manifest.json')['identities'])
    files=set(ROOT.glob('*.py'))|set(ROOT.glob('*.sbatch'))|set(ROOT.glob('*.sh'))|{ROOT/'PROTOCOL.md'}
    files.update(SOURCE/name for name in ('manifest.json','plan.json','verification.json'))
    files.update(Path(r['step']['result_path']) for r in rows)
    runtime=read(PARENT/'active_observation_model_v2/manifest.json')
    for path,digest in runtime['identities'].items():
        assert sha(path)==digest
        identities[path]=digest
    identities.update({str(p):sha(p) for p in files})
    value=dict(identities=identities,rows=rows,methods=list(METHODS),smoke=smoke_indices(rows),
        test_used=False,training_approved=False,shared_initial_executions=160,
        max_new_physical=66,max_model_calls=22,methods_trajectories=480)
    save(ROOT/'manifest.json',value)
    save(ROOT/'preflight.json',dict(passed=True,tests=result.testsRun,source_rows=160,
        failures=11,smoke=value['smoke'],source_audit_passed=True))
    print('PASS: 160 initial records, 480 planned trajectories, 11 initial failures',flush=True)


if __name__=='__main__':
    freeze()
