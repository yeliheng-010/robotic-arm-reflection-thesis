"""只重建已记录碰撞采样点，定位具体几何体，禁止用于模型答案标签。"""
import os
from pathlib import Path
from collections import Counter
import numpy as np
import mujoco
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from route_audit_v3 import rebuild
from cm_geometry import place_robot
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent.parent
NAMES = ('F0_964345_varied_noisy','F1_964345_varied_noisy','F1_964347_varied_noisy')


def contacts(model, data):
    rows = []
    for contact in data.contact[:data.ncon]:
        gids = [int(contact.geom1),int(contact.geom2)]
        bids = [int(model.geom_bodyid[g]) for g in gids]
        roots = [model.body(model.body_rootid[b]).name for b in bids]
        if not any(r in ('ur5e_base','2f85_base') for r in roots):
            continue
        if all(r in ('ur5e_base','2f85_base') for r in roots):
            continue
        rows.append(dict(bodies=[model.body(b).name for b in bids],
            geoms=[model.geom(g).name for g in gids], roots=roots, distance=float(contact.dist)))
    return rows


def inspect(name):
    source = PARENT/'qualification_strategy_v1/actual/cases'/name
    result = verify(source/'result.json')
    actual = read(source/'actual_plan.json')
    flow = rebuild(result['case'], actual)
    paths = [source/'result.json', source/'actual_plan.json']
    if name.startswith('F0'):
        path = PARENT/'clearance_pose_v1/probe/probe'/name/'plan.json'
        plan = read(path)
        row = plan['prefixes'][0]
        assert row['phase'] == 'pregrasp' and row['failure']['reason'] == 'collision'
        duration = actual['context']['parameters']['time_scale']
        joint = grasp.JointParameter(np.array(actual['context']['q0']), np.array(row['q1']))
        planner = grasp.TrajectoryPlanner(grasp.TrajectoryParameter(joint, grasp.QuinticVelocityParameter(duration)))
        q = planner.interpolate(row['time'])
        paths.append(path)
        phase = 'pregrasp_recorded_collision_time'
    else:
        stage = 'goals' if '964345' in name else 'grasps'
        row = next(r for r in actual['endpoints'][stage] if r.get('reason') == 'collision')
        q, phase = np.asarray(row['q']), stage+'_recorded_endpoint'
    place_robot(flow.robot, flow.env, flow.env.mj_data, q=q)
    collisions = contacts(flow.env.mj_model, flow.env.mj_data)
    assert collisions
    return dict(id=name, phase=phase, collisions=collisions,
        identities={str(p):sha(p) for p in paths})


def main():
    rows = [inspect(name) for name in NAMES]
    identities = {str(Path(__file__)):sha(Path(__file__))}
    for row in rows:
        identities.update(row.pop('identities'))
    save(ROOT/('result_'+os.environ['SLURM_JOB_ID']+'.json'), dict(rows=rows, identities=identities,
        physical_attempts=0, model_calls=0, purpose='private_engineering_audit_not_model_input'))
    for row in rows:
        pairs = Counter('|'.join(c['bodies']) for c in row['collisions'])
        print(dict(id=row['id'], phase=row['phase'], bodies=dict(pairs)), flush=True)


if __name__ == '__main__':
    main()
