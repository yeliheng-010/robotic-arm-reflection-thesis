"""自由关节四元数归一化，保留原矩阵/碰撞精度检查。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import mujoco
import ot_volume
import ot_endpoints

original_place=ot_volume.place


def place(model, data, *, source, initial, grasp, release):
    original_place(model,data,source=source,initial=initial,grasp=grasp,release=release)
    jid=int(model.body_jntadr[model.body(source).id])
    adr=int(model.jnt_qposadr[jid])+3
    quat=data.qpos[adr:adr+4]
    norm=float(np.linalg.norm(quat))
    assert np.isfinite(norm) and norm>0 and abs(norm-1.)<1e-12
    data.qpos[adr:adr+4]=quat/norm
    mujoco.mj_forward(model,data)


@contextmanager
def context():
    with patch.object(ot_volume,'place',place),patch.object(ot_endpoints,'place',place):
        yield
