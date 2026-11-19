"""探测各类错误注入在 MuJoCo 中是否会产生真实的物理失败。

用法: python experiments/probes/fault_physics_probe.py OBJ DST BIAS_X BIAS_Y DIVIDER_H LIFT
  BIAS_X/BIAS_Y: 手眼标定偏差（米），同时作用于抓取与放置
  DIVIDER_H:     隔板高度（米，0 表示保持原状）
  LIFT:          抓取后的抬升高度（米）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
for p in ['graspnet-baseline/models', 'graspnet-baseline/dataset', 'graspnet-baseline/utils', 'manipulator_grasp', '.']:
    sys.path.insert(0, os.path.join(ROOT, p))
os.environ.setdefault('GRASP_BACKEND', 'geometric')

import cv2
import numpy as np
import spatialmath as sm

from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from grasp_process import run_grasp_inference, GraspFlow, camera_calibration_from_env
from vlm_process import segment_and_crop_mask

obj, dst = sys.argv[1], sys.argv[2]
bx, by, div_h, lift = map(float, sys.argv[3:7])


def editor(spec):
    if div_h > 0:
        g = spec.geom('safety_divider')
        g.size = [g.size[0], g.size[1], div_h / 2]
        g.pos = [g.pos[0], g.pos[1], div_h / 2]


env = UR5GraspEnv(headless=True, model_editor=editor)
env.reset()
m, d = env.mj_model, env.mj_data
for _ in range(500):
    env.step()
imgs = env.render()
color = cv2.cvtColor(imgs['img'], cv2.COLOR_RGB2BGR)
depth = imgs['depth']
T, K = camera_calibration_from_env(env, depth.shape)
g = m.body(obj).id
pc = T.inv() * d.xpos[g]
uv = (int(K[0] * pc[0] / pc[2] + K[2]), int(K[1] * pc[1] / pc[2] + K[3]))
mask = segment_and_crop_mask(image_bgr=color, point_xy=uv, depth=depth, save_path='mask_final.png')
gg = run_grasp_inference(color, depth, mask, fovy=np.deg2rad(58))
flow = GraspFlow(env, gg)
flow.T_wo = sm.SE3.Trans(bx, by, 0) * flow.T_wo

div_id = m.body('SafetyDivider').id
hits = set()
orig_step = env.step


def step(a=None):
    orig_step(a)
    for c in d.contact[:d.ncon]:
        b1 = m.body_rootid[m.geom_bodyid[c.geom1]]
        b2 = m.body_rootid[m.geom_bodyid[c.geom2]]
        if div_id in (b1, b2):
            hits.add(m.body(b1 if b2 == div_id else b2).name)


env.step = step
status = 'ok'
c_close = c_carry = -1.0
try:
    flow.move_to_grasp_pose()
    flow.close_gripper()
    c_close = float(d.joint('right_driver_joint').qpos[0])
    tgt = d.xpos[m.body(dst).id].copy() + np.array([bx, by, 0])
    flow.move_to_point(tuple(tgt), z_offset=0.12, lift_height=lift)
    c_carry = float(d.joint('right_driver_joint').qpos[0])
    held = float(np.linalg.norm(d.xpos[g] - env.robot.get_cartesian().t))
    flow.open_gripper()
    for _ in range(250):
        env.step(flow.action)
    flow.back_to_zero()
except AssertionError:
    status = 'IK_FAIL'
    held = -1.0
fin = d.xpos[g]
center = d.xpos[m.body(dst).id]
print('RESULT', obj, dst, 'bias', bx, by, 'div', div_h, 'lift', lift, status,
      'closure', round(c_close, 3), round(c_carry, 3), 'held_dist', round(held, 3),
      'final_xy_err', round(float(np.linalg.norm(fin[:2] - center[:2])), 3),
      'z', round(float(fin[2]), 3), 'divider_hits', sorted(hits))
