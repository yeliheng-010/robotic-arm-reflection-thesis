import unittest
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
import rv_runtime
from top_runtime import candidates
from cp_candidates import candidates as expanded
from jv_context import observation,stage,CURRENT


class StageTests(unittest.TestCase):
    def test_separate_candidate_ledgers_same_points(self):
        points=np.array([[1.+x,.5+y,.8] for x in np.linspace(-.02,.02,12)
                         for y in np.linspace(-.03,.03,12)])
        before=points.copy()
        trace={}
        def measured():
            rows=rv_runtime.poses(sm.SE3(1.,.5,.8))
            self.assertEqual(len(rows),len(rv_runtime.poses(sm.SE3(1.,.5,.8))))
            return rows
        with observation(points,trace):
            first=stage(candidates,measured)
            second=stage(expanded,measured)
        self.assertEqual(2,len(first))
        self.assertGreater(len(second),len(first))
        self.assertEqual(2,len(trace['candidate_stages']))
        self.assertEqual(trace['candidate_stages'][-1]['poses'],trace['poses'])
        np.testing.assert_array_equal(before,points)

    def test_context_is_reset_after_error(self):
        with self.assertRaises(RuntimeError):
            with observation(np.zeros((0,3)),{}):
                raise RuntimeError('forced')
        with self.assertRaises(LookupError):
            CURRENT.get()


if __name__ == '__main__':
    unittest.main(verbosity=2)
