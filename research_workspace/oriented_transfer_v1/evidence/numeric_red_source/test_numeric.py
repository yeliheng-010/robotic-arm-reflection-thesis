"""实际失败端点回归；转换失败不能伪装成规划拒绝。"""
import unittest
from itertools import islice
from reflection.__main__ import bootstrap
bootstrap()
import ot_endpoints
from ot_inputs import opened
from ot_register import RUN,verify
from goal_geometry import geometry
from ot_volume import corners
from ot_volume_v2 import context


class NumericTests(unittest.TestCase):
    def test_actual_rotated_endpoint_is_representable(self):
        entry=verify(RUN/'manifest.json')['rows'][0]
        count=sum(1 for _ in (RUN/'probe/capsule_964345/endpoints.jsonl').open())
        converted=False
        with opened(entry) as (flow,grasps,poses),context():
            points=corners(flow.env.mj_model,flow.env.mj_data,entry['case']['item']['source'])
            choices=ot_endpoints.candidates(grasps,poses,points=points,dimensions=geometry(flow,entry['case']['item']))
            candidate=next(islice(choices,count,None))
            try:
                result=ot_endpoints.measure(flow,poses[candidate['grasp']['pose']],candidate['release'],
                    item=entry['case']['item'],config=candidate['grasp']['config'])
                converted=isinstance(result['ok'],bool) and len(result['held_pose'])==4
            except ValueError as error:
                self.assertEqual('expecting SO3 or rotation matrix',str(error))
        self.assertTrue(converted,'Valid rigid rotation must remain representable after quaternion storage')


if __name__=='__main__':
    unittest.main(verbosity=2)
