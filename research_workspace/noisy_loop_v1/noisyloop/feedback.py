"""调用冻结噪声投影，方法与幅度之间共享预登记随机数。"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import numpy as np

SOURCE=Path('/home/yeliheng/grasp_server/noise_feedback_v1/projection.py')
spec=importlib.util.spec_from_file_location('frozen_residual_projection',SOURCE)
projection=importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)
SEED_NAMESPACE=908000
FACTORS={'position_only':0,'yaw_only':1}


def seed_for(item,index):
    entropy=[SEED_NAMESPACE,item['seed'],FACTORS[item['factor']],item['noise_repeat'],index]
    return int(np.random.SeedSequence(entropy).generate_state(1)[0])


def project_step(step,item):
    result=deepcopy(step)
    result['projection_seed']=seed_for(item,step['index'])
    result['noise_audit']={}
    if step['feedback'] is not None:
        result['feedback'],result['noise_audit']=projection.project(
            step['feedback'],item['noise_profile'],seed=result['projection_seed'])
    return result
