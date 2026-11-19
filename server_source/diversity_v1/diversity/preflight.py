"""真实渲染与初态检查；不调用模型、不按成功率筛选场景。"""
import json
import os
from pathlib import Path
import cv2
import mujoco
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from reflection.fault_injection import Fault
from reflection.sim_sensing import SegmentationRenderer
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from diversity.config import scenario, pilot_tasks
from diversity.scene import ScenarioFault
from diversity.noise import corrupt_depth
from stability.collection_status import atomic
from diversity.overview import make_overview

ROOT = Path('/home/yeliheng/grasp_server/diversity_v1/preflight')
SETTLE_STEPS = 500
MIN_VISIBLE_PIXELS = 60


def check(index, task):
    config = scenario(task['seed'], task['level'])
    fault = ScenarioFault(Fault(task['fault'], task['source'], task['seed'], 0), config)
    env = UR5GraspEnv(headless=True, model_editor=fault.model_editor)
    directory = ROOT/f'{index:02d}'
    directory.mkdir(exist_ok=False)
    try:
        env.reset()
        for _ in range(SETTLE_STEPS):
            env.step()
        observation = env.render()
        renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
        try:
            root_map = renderer.root_map(env.mj_data)
        finally:
            renderer.close()
        pixels = int((root_map == env.mj_model.body(task['source']).id).sum())
        noisy, noise = corrupt_depth(observation['depth'], config['profile'],
                                    seed=np.random.SeedSequence([task['seed'], 301, 1, 0]))
        np.savez_compressed(directory/'depth.npz', clean=observation['depth'], noisy=noisy)
        cv2.imwrite(str(directory/'scene.png'), cv2.cvtColor(observation['img'], cv2.COLOR_RGB2BGR))
        position = env.mj_data.body(task['source']).xpos.tolist()
        valid = bool(np.isfinite(env.mj_data.qpos).all() and position[2] > .74 and pixels >= MIN_VISIBLE_PIXELS)
        result = dict(case=index, task=task, scenario=config, passed=valid,
                      target_visible_pixels=pixels, target_xyz=position, noise=noise,
                      check_scope='finite settled state, target above table, visible in segmentation; not IK success')
        atomic(directory/'result.json', result)
        return result
    finally:
        env.close()


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Render through Slurm'
    ROOT.mkdir(exist_ok=False)
    rows = []
    for index, task in enumerate(pilot_tasks()):
        rows.append(check(index, task))
        atomic(ROOT/'progress.json', dict(completed=len(rows), total=16, rows=rows))
        print(json.dumps({k: rows[-1][k] for k in ('case', 'passed', 'target_visible_pixels')}), flush=True)
    result = dict(passed=all(r['passed'] for r in rows), cases=len(rows), rows=rows, test_used=False)
    atomic(ROOT/'result.json', result)
    make_overview(ROOT, rows)
    assert result['passed'], 'Preflight failed; preserve evidence and review before pilot'


if __name__ == '__main__':
    main()

