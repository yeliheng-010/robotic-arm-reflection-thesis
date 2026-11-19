"""一次性诊断：保持相机/深度不变，仅排除分割轮廓像素。"""
import cv2
import numpy as np
from sd_config import factors, MOVING
from sd_scene import apply
from sd_runtime import context
from sd_render import depth_check
from reflection.sim_sensing import SegmentationRenderer
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv


def eroded(roots, env, size):
    interior = np.full_like(roots, -1)
    for name in MOVING:
        bid = env.mj_model.body(name).id
        mask = cv2.erode((roots==bid).astype('uint8'), np.ones((size,size),'uint8'))
        interior[mask>0] = bid
    return interior


def main():
    config = factors(960101, 'baseline')
    with context(config):
        env = UR5GraspEnv(headless=True, model_editor=lambda spec: apply(spec, config))
        renderer = None
        try:
            env.reset()
            for _ in range(500):
                env.step()
            observation = env.render()
            renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
            roots = renderer.root_map(env.mj_data)
            print('raw', depth_check(env, observation['depth'], roots), flush=True)
            for size in (3, 5):
                interior = eroded(roots, env, size)
                print('kernel', size, depth_check(env, observation['depth'], interior), flush=True)
        finally:
            if renderer is not None:
                renderer.close()
            env.close()


if __name__ == '__main__':
    main()
