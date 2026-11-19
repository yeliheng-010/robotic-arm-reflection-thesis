"""验证能力约束、历史原样保留和服务错误分类。"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from reflection.errors import ErrorReport, ErrorType
from reflection.reflector import Parameters, Reflection
from controlled.config import scenario
from controlled.feedback import check_action, ProjectedReflector
from controlled.client import ControlledFlash
from controlled.worker import summary


class ReflectorTests(unittest.TestCase):
    def test_disabled_actions_noop_and_candidate_bounds(self):
        for change in ({'replan': True}, {'reground': True}, {'lift_height': .35}, {'candidate_index': 3}):
            with self.assertRaises(ValueError):
                check_action(Reflection('cause', change, 'llm'), Parameters(), candidate_count=3)
        answer = Reflection('cause', {'lift_height': .45}, 'llm')
        self.assertIs(answer, check_action(answer, Parameters(), candidate_count=3))

    def test_history_is_previous_observation_not_new_truth(self):
        class Inner:
            def reflect(self, report, parameters, history=()):
                return Reflection('test', {'lift_height': .45 if not history else .48}, 'rule')
        report = ErrorReport(ErrorType.EMPTY_GRASP, 'private', {'grasp_residual_xy': [.04, .02]})
        with tempfile.TemporaryDirectory() as temp:
            wrapper = ProjectedReflector(Inner(), scenario(82000, 'feedback'), directory=Path(temp))
            wrapper.reflect(report, Parameters())
            first = json.loads(json.dumps(wrapper.history[0]['error']))
            report.evidence['grasp_residual_xy'] = [.2, .2]
            wrapper.reflect(report, Parameters().updated({'lift_height': .45}))
            self.assertEqual(first, wrapper.history[0]['error'])
            self.assertNotEqual(first, wrapper.history[1]['error'])

    def test_service_failure_is_not_invalid_output(self):
        report = ErrorReport(ErrorType.EMPTY_GRASP, 'failed', {'diagnostics': {}})
        event = {'error': 'connection refused', 'service_error': True, 'elapsed_s': .1}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            reflector = ControlledFlash('task', directory)
            with patch('controlled.client.generate', return_value=event), self.assertRaises(RuntimeError):
                reflector.reflect(report, Parameters())
            record = dict(accepted=False, error={'error_type': 'empty_grasp'}, reflection_error='service')
            result = dict(records=[record], success=False, elapsed_s=1)
            row = summary(result, directory, case=0, arm='flash', task={})
            self.assertEqual(1, row['service_errors'])
            self.assertEqual(0, row['invalid_outputs'])


if __name__ == '__main__':
    unittest.main()
