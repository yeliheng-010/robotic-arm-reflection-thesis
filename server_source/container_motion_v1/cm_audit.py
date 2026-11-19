"""重建状态转移与执行检查，精确区分共享尝试和方法轨迹。"""
from pathlib import Path
from loopstudy.actions import initial
from rc_audit import check_step
from rc_policy import decide
from cl_geometry import verify_compiled
from cd_physics_audit import outcome
from cm_common import ROOT, METHODS, read
from cm_replay import check_extension


def motion(step, source, plan, *, policy, feedback):
    check_step(step,source,plan)
    record = read(step['result_path'])['records'][0]
    layout = plan['layouts'][str(source['item']['seed'])]
    return check_extension(record,source['item'],layout,policy=policy,feedback=feedback)


def check_files(folder, steps):
    paths = {Path(s['result_path']) for s in steps}
    assert all(p.is_relative_to(folder) for p in paths)
    assert set(folder.glob('*/result.json'))==paths, 'Unaccounted physical runs'
    return len(paths)


def development(result, manifest):
    case = manifest['cases'][result['index']]
    assert result['item']==case['source']['item'] and result['status']=='completed'
    assert not result['test_used'] and not result['training_approved']
    assert set(result['steps'])==set(METHODS)
    checked = {}
    for method,step in result['steps'].items():
        assert step['index']==3 and step['state']==case['rule_action']['state']
        checked[method] = motion(step,case['source'],manifest['development_plan'],
            policy=method,feedback=case['snapshot']['feedback'])
    assert outcome(result['steps']['rule'])==outcome(case['rule_final']), 'Rule replay changed'
    folder = ROOT/'development'/result['item']['id']
    count = check_files(folder,result['steps'].values())
    return dict(index=result['index'],id=result['item']['id'],passed=True,new_physical=count,
        success={m:s['success'] for m,s in result['steps'].items()},motion=checked)


def check_shared(result, manifest):
    source,shared,decisions = result['source'],result['shared'],result['decisions']
    assert 1<=len(shared)<=2 and shared[0]==source['step']
    assert shared[0]['state']==initial() and shared[0]['index']==1
    for step in shared:
        check_step(step,source,manifest['validation_plan'])
        assert 'motion_extension' not in read(step['result_path'])['records'][0]
    for i,decision in enumerate(decisions):
        assert not shared[i]['success']
        assert decision==decide(shared[:i+1],decisions[:i],method='rule')
    if len(shared)==2:
        assert shared[1]['state']==decisions[0]['selected']['state'] and shared[1]['index']==2
    assert len(decisions)==sum(not s['success'] for s in shared)


def method_steps(result, manifest, method):
    shared,decisions = result['shared'],result['decisions']
    steps = result['steps'][method]
    assert steps[:len(shared)]==shared and len(shared)<=len(steps)<=3
    needs_third = len(shared)==2 and not shared[-1]['success'] and decisions[-1]['selected'] is not None
    assert (len(steps)==3)==needs_third
    if not needs_third:
        return dict(active=False,selected=None,fallback=None)
    assert steps[-1]['state']==decisions[-1]['selected']['state'] and steps[-1]['index']==3
    return motion(steps[-1],result['source'],manifest['validation_plan'],
        policy=method,feedback=shared[-1]['feedback'])


def validation(result, manifest):
    item = manifest['validation_plan']['items'][result['index']]
    assert result['item']==result['source']['item']==item and result['status']=='completed'
    assert result['source']['index']==result['index'] and set(result['steps'])==set(METHODS)
    assert not result['test_used'] and not result['training_approved']
    plan = manifest['validation_plan']
    expected_geometry = verify_compiled(item,plan['layouts'][str(item['seed'])],plan['geometry'])
    assert result['source']['geometry']==expected_geometry
    assert result['source']['success']==result['shared'][0]['success']
    check_shared(result,manifest)
    checked = {method:method_steps(result,manifest,method) for method in METHODS}
    folder = ROOT/'validation'/item['id']
    count = check_files(folder,[s for steps in result['steps'].values() for s in steps])
    return dict(index=result['index'],id=item['id'],passed=True,new_physical=count,
        shared_physical=len(result['shared']),success={m:s[-1]['success'] for m,s in result['steps'].items()},
        first_success=result['shared'][0]['success'],motion=checked)
