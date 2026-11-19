"""真实传感器预览；深度噪声不伪装为 RGB 颜色变化。"""
import cv2
from diversity.runtime import sensor_context
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from sd_runtime import context
from sd_scene import apply
from sd_common import save
from pair_runtime import engine_config

SETTLE_STEPS = 500


def render(config, folder):
    folder.mkdir(parents=True, exist_ok=False)
    trace = []
    with context(config), sensor_context(engine_config(config), 1, directory=folder, trace=trace):
        env = UR5GraspEnv(headless=True, model_editor=lambda spec: apply(spec, config))
        try:
            env.reset()
            for _ in range(SETTLE_STEPS):
                env.step()
            observation = env.render()
            image = cv2.cvtColor(observation['img'], cv2.COLOR_RGB2BGR)
            if not cv2.imwrite(str(folder/'rgb.png'), image):
                raise RuntimeError('Failed to save actual scene preview')
        finally:
            env.close()
    save(folder/'sensor_trace.json', trace)
    return trace
