"""在独立数据副本核对碰撞瞬间的理想路径净空，不推进物理。"""
import os
from types import SimpleNamespace
import numpy as np
import mujoco
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from sd_common import read, save, sha
from sd_scene import compiled
from manipulator_grasp.arm.robot import UR5e
from cm_geometry import place_robot
from contact_data import geom_info
from contrast_run import read_trace
from diagnostic_run import ROOT


def inspect(model, data):
    pad, knife = model.geom('left_pad1').id, model.geom('knife_contact1').id
    segment = np.zeros(6)
    distance = mujoco.mj_geomDistance(model, data, pad, knife, .1, segment)
    return dict(distance=float(distance), closest_segment=segment.tolist(),
                pad=geom_info(model, data, pad), knife=geom_info(model, data, knife))


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = read(ROOT/'manifest.json')
    case = next(c for c in manifest['cases'] if c['item']['id'] == '961108_varied_noisy_1')
    record = read(case['step']['result_path'])['records'][0]
    context = record['motion_extension']['context']
    model, data = compiled(case['config'])
    data.qpos[:] = context['qpos']
    mujoco.mj_forward(model, data)
    robot = UR5e()
    robot._base = sm.SE3(np.array(context['base']))
    robot.robot.base = robot._base
    robot.set_tool(sm.SE3(np.array(context['tool'])))
    env = SimpleNamespace(mj_model=model, joint_names=context['joint_names'])
    rows = read_trace(ROOT/'physics'/case['item']['id']/'contacts.jsonl')
    final = rows[-1]
    result = dict(id=case['item']['id'], time=final['time'],
                  actual_pad=next(g for g in final['pad_geometry'] if g['name'] == 'left_pad1'),
                  actual_contacts=[c for c in final['contacts'] if 'Knife' in c['roots']],
                  source_sha256=sha(case['step']['result_path']))
    for name, q in (('commanded_joints', final['ctrl'][:6]), ('actual_arm_joints', final['qpos'])):
        data.qpos[:] = context['qpos']
        place_robot(robot, env, data, q=np.array(q))
        result[name] = inspect(model, data)
    result['limitation'] = 'static initial finger joints and rigid flange; actual pad geometry comes from telemetry'
    save(ROOT/'static_contact_probe.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
