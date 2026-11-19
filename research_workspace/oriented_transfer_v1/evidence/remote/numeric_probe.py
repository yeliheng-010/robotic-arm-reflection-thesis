"""只复现首次端点矩阵失败，输出数值误差而非绕过校验。"""
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import ot_endpoints
from ot_inputs import opened
from ot_register import RUN,verify
from goal_geometry import geometry
from ot_volume import corners


def main():
    entry=verify(RUN/'manifest.json')['rows'][0]
    with opened(entry) as (flow,grasps,poses):
        points=corners(flow.env.mj_model,flow.env.mj_data,entry['case']['item']['source'])
        candidate=next(ot_endpoints.candidates(grasps,poses,points=points,dimensions=geometry(flow,entry['case']['item'])))
        original=ot_endpoints.body_pose
        def measured(model,data,source):
            rotation=data.body(source).xmat.reshape(3,3)
            print(dict(orthogonality_max=float(np.max(np.abs(rotation.T@rotation-np.eye(3)))),
                determinant=float(np.linalg.det(rotation)),finite=bool(np.isfinite(rotation).all())),flush=True)
            return original(model,data,source)
        with patch.object(ot_endpoints,'body_pose',measured):
            ot_endpoints.measure(flow,poses[candidate['grasp']['pose']],candidate['release'],
                item=entry['case']['item'],config=candidate['grasp']['config'])


if __name__=='__main__':
    main()
