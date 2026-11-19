from pathlib import Path
import mujoco
import numpy as np
from sd_common import read,save
from sd_runtime import context
from sd_scene import apply
from sd_inventory import root_boxes
from sd_config import MOVING
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from sf_camera import proposal
root=Path('/home/yeliheng/grasp_server')
config=read(root/'scene_pair_validation_v1/manifest.json')['configs']['961101_varied_noisy']
old=read(root/'scene_pair_feasibility_v2/selection/961101/selection.json')
with context(config):
    env=UR5GraspEnv(headless=True,model_editor=lambda spec:apply(spec,config))
    try:
        env.reset()
        for _ in range(500): env.step()
        before={k:v for k,v in root_boxes(env.mj_model,env.mj_data).items() if k in MOVING}
        mujoco.mj_forward(env.mj_model,env.mj_data)
        after={k:v for k,v in root_boxes(env.mj_model,env.mj_data).items() if k in MOVING}
        result=dict(before_delta={k:float(np.max(np.abs(np.array(v)-old['settled_boxes'][k]))) for k,v in before.items()},after_delta={k:float(np.max(np.abs(np.array(v)-old['settled_boxes'][k]))) for k,v in after.items()},proposal_matches_before=proposal(961101,1,boxes=before)==old['attempts'][1]['camera'],proposal_matches_after=proposal(961101,1,boxes=after)==old['attempts'][1]['camera'])
        save(root/'scene_pair_feasibility_v3/diagnosis_5765.json',result)
        print(result,flush=True)
    finally: env.close()
