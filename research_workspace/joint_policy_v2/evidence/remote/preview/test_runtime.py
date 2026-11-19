import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from rh_planner import planners
from waypoint_runtime import prefix_wrapper
from jg_runtime import prefix_factory


class RuntimeTests(unittest.TestCase):
    def exercise(self, selected):
        option=dict(waypoints=[[0.]*6,[.3]*6],durations=[1.5])
        original=planners(option)[0]
        robot,env,action=object(),object(),object()
        values=(robot,env,[original],[0.,1.5],action,.002)
        calls=[]
        def backend(*args):
            calls.append(args)
            return args[4]
        def hook():
            for _ in range(3):
                grasp._run_planners(*values)
            return action
        trace=dict(selected=dict(approach_route='direct',**selected),edges=[[0.,0.],[1.,1.]])
        with patch.object(grasp,'_run_planners',backend):
            result=prefix_factory(prefix_wrapper)(hook,trace)()
        self.assertIs(action,result)
        self.assertEqual(3,len(calls))
        for row in calls:
            self.assertIs(robot,row[0])
            self.assertIs(env,row[1])
            self.assertIs(action,row[4])
        return calls,original

    def test_primary_preserves_all_original_commands(self):
        rows,planner=self.exercise({})
        for row in rows:
            self.assertIs(planner,row[2][0])
            self.assertEqual([0.,1.5],row[3])

    def test_fallback_replaces_only_first_segment(self):
        option=dict(id='equivalent_joint_angles',waypoints=[[0.]*6,[.3]*6],durations=[3.])
        rows,planner=self.exercise(dict(joint_option=option))
        self.assertEqual([0.,3.],rows[0][3])
        for row in rows[1:]:
            self.assertIs(planner,row[2][0])
            self.assertEqual([0.,1.5],row[3])


if __name__ == '__main__':
    unittest.main(verbosity=2)
