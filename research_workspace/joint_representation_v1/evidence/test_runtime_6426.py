import unittest
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from js_geometry import option
from rh_planner import planners
from jp_runtime import replace


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.path = [[0.]*6,[1.]*6]
        self.selection = dict(path=self.path,option=option(self.path,1.5))
        self.values = [object(),object(),planners(option(self.path,1.5)),[0.,1.5],object(),.002]

    def test_replacement_keeps_robot_action_and_time_step(self):
        result = replace(self.values,self.selection)
        for index in (0,1,4,5):
            self.assertIs(self.values[index],result[index])
        self.assertEqual([0.,*self.selection['option']['durations']],result[3])
        np.testing.assert_allclose(self.path[-1],result[2][0].interpolate(result[3][-1]),atol=1e-12)

    def test_wrong_target_fails_closed(self):
        wrong = dict(self.selection,path=[self.path[0],[2.]*6])
        with self.assertRaises(AssertionError):
            replace(self.values,wrong)

    def test_wrong_start_fails_closed(self):
        wrong = dict(self.selection,path=[[.1]*6,self.path[1]])
        with self.assertRaises(AssertionError):
            replace(self.values,wrong)


if __name__ == '__main__':
    unittest.main(verbosity=2)
