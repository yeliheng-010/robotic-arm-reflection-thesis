"""验证新路径替换边界、时间参数与源码规模；不启动物理任务。"""
import ast
import math
import unittest
from pathlib import Path
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from rh_planner import planners
from js_geometry import duration, option
from js_scope import wrapper

ROOT = Path(__file__).resolve().parents[1]


class WiringTests(unittest.TestCase):
    def rows(self, path):
        return [('pregrasp',planners(option([path[0],path[-1]],1.5))[0],1.5),
                ('approach',object(),1.5),('grasp',object(),1.5)]

    def test_only_matching_pregrasp_changes(self):
        path = [[0.]*6,[.1]*6,[.2]*6]
        original = self.rows(path)
        rows = wrapper(lambda *a,**k: original,dict(path=path))(None,None)
        self.assertEqual(4,len(rows))
        self.assertEqual(original[1:],rows[2:])
        for index,(_,planner,seconds) in enumerate(rows[:2]):
            np.testing.assert_allclose(path[index],planner.interpolate(0.),atol=1e-12)
            np.testing.assert_allclose(path[index+1],planner.interpolate(seconds),atol=1e-12)

    def test_other_start_or_goal_preserves_original(self):
        path = [[0.]*6,[.1]*6,[.2]*6]
        for other in ([[.01]*6,path[-1]],[path[0],[.21]*6]):
            original = self.rows(other)
            result = wrapper(lambda *a,**k: original,dict(path=path))(None,None)
            self.assertIs(original,result)

    def test_quintic_limits_and_original_minimum(self):
        for delta in (0.,.01,1.,6.,12.):
            seconds = duration([0.]*6,[delta]*6,1.5)
            self.assertGreaterEqual(seconds,1.5)
            self.assertLessEqual(1.875*delta/seconds,1.+1e-12)
            self.assertLessEqual((10/math.sqrt(3))*delta/seconds**2,2.+1e-12)

    def test_code_size_gate(self):
        for path in ROOT.glob('*.py'):
            source = path.read_text()
            self.assertLessEqual(len(source.splitlines()),300,path.name)
            for node in ast.walk(ast.parse(source)):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    self.assertLessEqual(node.end_lineno-node.lineno+1,50,(path.name,node.name))
                    self.assertLessEqual(len(node.args.posonlyargs+node.args.args),3,(path.name,node.name))


if __name__ == '__main__':
    unittest.main(verbosity=2)
