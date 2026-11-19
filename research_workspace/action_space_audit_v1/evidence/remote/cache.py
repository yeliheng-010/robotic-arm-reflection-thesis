"""只复用同动作、同姿态的已审计端点。"""
from copy import deepcopy
import numpy as np


def reused(proposal, saved):
    if proposal['action'] != saved['proposal']['action']:
        return None
    if not np.array_equal(proposal['pose'],saved['proposal']['pose']):
        raise ValueError('Cached action has different geometry')
    return deepcopy(saved['endpoints'])
