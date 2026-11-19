"""共享投影算子，新增场景采用独立且方法配对的随机流。"""
from copy import deepcopy
import numpy as np
from noisyloop.feedback import projection

NOISE_NAMESPACE=920800


def project_step(step,item):
    value=deepcopy(step)
    entropy=[NOISE_NAMESPACE,item['seed'],item['factor_index'],step['index']]
    value['projection_seed']=int(np.random.SeedSequence(entropy).generate_state(1)[0])
    value['noise_audit']={}
    if step['feedback'] is not None:
        value['feedback'],value['noise_audit']=projection.project(step['feedback'],
            item['noise_profile'],seed=value['projection_seed'])
    return value
