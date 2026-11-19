"""执行前按同一有限规划器筛查任务可行性；不以真实执行成败换种子。"""
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import goal_search
import nc_prepare
from pilot import extract_seeds
from audit_motion_live import UR5e, set_robot_config, guard_context
from route_audit_v3 import rebuild
from cm_geometry import place_robot
from goal_geometry import geometry
from rv_runtime import mode
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from sr_common import read, save, sha, change

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_self_route_v1'
SEEDS = tuple(range(962701,962709))


def reference(case, template):
    # 只复用已验证的机器人标定和初始关节，不复制旧场景物体位置。
    from sd_scene import compiled
    model, data = compiled(case['config'])
    robot = UR5e()
    robot._base = sm.SE3(np.array(template['base']))
    robot.robot.base = robot._base
    robot.set_tool(sm.SE3(np.array(template['tool'])))
    q0, q1 = np.array(template['q0']), np.array(template['q1'])
    robot.set_joint(q0)
    env = SimpleNamespace(mj_model=model,mj_data=data,joint_names=template['joint_names'])
    place_robot(robot,env,data,q=q0)
    flow = SimpleNamespace(robot=robot,env=env,q0=q0,q1=q1,T_wo=sm.SE3())
    dimensions = geometry(flow,case['item'])
    center = np.array(dimensions['source_center'])
    center[2] += dimensions['source_half'][2]
    rotation = sm.SO3.TwoVectors(x=[0.,0.,-1.],y=[1.,0.,0.])
    flow.T_wo = sm.SE3.Rt(rotation,center)
    return flow


def qualify(case, template):
    name = case['item']['id']
    if not case['config']['geometry_accepted'] or not case['config']['compiled_check']['passed']:
        return dict(id=name,passed=False,status='layout_geometry_rejected')
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}), \
         self_context(),joint_context(case['config']),mode(dict(grasp_mode='world_down')), \
         patch.object(goal_search,'LIFTS',(.15,)):
        flow = reference(case,template)
        state,_ = change(case['state'],dict(grasp_mode='original'),action='SELF_SAFE_ROUTE')
        plan = goal_search.choose(flow,item=case['item'],parameters=state['parameters'],
            hooks=(grasp.move_to_grasp_pose,grasp.move_to_point))
    path = ROOT/'plans'/(name+'.json')
    save(path,plan)
    return dict(id=name,passed=plan['selected'] is not None,status=plan['status'],
        passing_endpoints=plan['endpoints']['passing'],selected=(plan['selected'] or {}).get('id'),
        path=str(path),sha256=sha(path))


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    paths = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    used = set()
    for path in paths:
        used.update(extract_seeds(read(path)))
    assert not used.intersection(SEEDS)
    template_path = SOURCE/'cases/S0_962601_baseline/attempt_2/route.json'
    audit = read(SOURCE/'audit_962601.json')
    assert sha(template_path)==audit['identities'][str(template_path)]
    template = read(template_path)['context']
    with patch.object(nc_prepare,'SEEDS',SEEDS):
        cases = nc_prepare.cases()
    cases = [c for c in cases if c['item']['group']=='varied_noisy' or c['item']['seed']==SEEDS[0]]
    for case in cases:
        case['item']['id']='Q'+case['item']['id'][1:]
        case['item']['split']='reserved_engineering_preflight_not_training'
    identities = {str(p):sha(p) for p in ROOT.iterdir() if p.suffix in ('.py','.sbatch','.md')}
    for folder in ('natural_joint_guard_v1','natural_self_guard_v1'):
        identities.update({str(p):sha(p) for p in (ROOT.parent/folder).glob('*.py')})
    identities[str(template_path)] = sha(template_path)
    save(ROOT/'manifest.json',dict(cases=cases,seeds=list(SEEDS),identities=identities,
        seed_isolation=dict(scanned=len(paths),overlap=False),physical_attempts=0,model_calls=0,
        reserved_for_new_physics=True,training_ready=False,
        reference_source='simulation_geometry_only_for_preflight_not_model_input'))
    rows=[]
    for case in cases:
        (ROOT/'status.json').write_text(case['item']['id'],encoding='utf-8')
        row=qualify(case,template)
        rows.append(row)
        print(row,flush=True)
        save(ROOT/'results'/(case['item']['id']+'.json'),row)
    assert all(sha(p)==h for p,h in identities.items())
    save(ROOT/'result.json',dict(rows=rows,physical_attempts=0,model_calls=0,training_ready=False,
        limitation='Finite nominal geometric search; rejects are not proof of global impossibility; passes are not physical success'))


if __name__=='__main__':
    main()
