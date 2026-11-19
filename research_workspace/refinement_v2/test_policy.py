"""规则边界、缺失测量与新提示必须接受真实约束测试。"""
import copy
import json
import unittest
from reflection.errors import ErrorReport, ErrorType
from reflection.reflector import Parameters, RuleReflector
from controlled.client import messages as original_messages
from controlled.feedback import check_action
from refinement.policy import BoundedRule, PolicyExhausted
from refinement.client import messages
from refinement.audit import compare_saved


def report(kind, **evidence):
    return ErrorReport(kind, 'failure', evidence)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = BoundedRule()
        self.parameters = Parameters()

    def test_missing_placement_is_explicit_probe_not_zero(self):
        r = report(ErrorType.OBJECT_OUTSIDE_CONTAINER)
        old = RuleReflector().reflect(r, self.parameters)
        with self.assertRaises(ValueError):
            check_action(old, self.parameters)
        answer = self.policy.reflect(r, self.parameters)
        self.assertEqual('rule_v2', answer.source)
        self.assertIn('missing_measurement_probe', answer.cause)
        self.assertEqual([.02, 0., 0.], answer.changes['place_offset'])
        check_action(answer, self.parameters)

    def test_measured_zero_is_not_missing(self):
        r = report(ErrorType.OBJECT_OUTSIDE_CONTAINER, placement_residual_xy=[0., 0.])
        answer = self.policy.reflect(r, self.parameters)
        self.assertNotIn('missing_measurement_probe', answer.cause)
        self.assertNotIn('place_offset', answer.changes)

    def test_out_of_range_compensation_is_explicitly_bounded(self):
        r = report(ErrorType.OBJECT_OUTSIDE_CONTAINER, placement_residual_xy=[.31, -.04])
        with self.assertRaises(ValueError):
            RuleReflector().reflect(r, self.parameters)
        answer = self.policy.reflect(r, self.parameters)
        self.assertEqual([-.25, .04, 0.], answer.changes['place_offset'])
        check_action(answer, self.parameters)

    def test_pregrasp_collision_does_not_modify_future_lift(self):
        r = report(ErrorType.COLLISION, grasp_residual_xy=[-.026, -.039],
                   diagnostics={'motion_segment': 'grasp', 'available_candidate_count': 5})
        answer = self.policy.reflect(r, self.parameters)
        self.assertEqual([.026, .039, 0.], answer.changes['grasp_offset'])
        self.assertNotIn('lift_height', answer.changes)

    def test_transport_collision_uses_lift(self):
        r = report(ErrorType.COLLISION, diagnostics={'motion_segment': 'transport'})
        self.assertEqual({'lift_height': .45}, self.policy.reflect(r, self.parameters).changes)

    def test_candidate_count_and_exhaustion(self):
        r = report(ErrorType.EMPTY_GRASP, grasp_residual_xy=[0., 0.],
                   diagnostics={'available_candidate_count': 1, 'motion_segment': 'grasp'})
        answer = self.policy.reflect(r, self.parameters)
        check_action(answer, self.parameters, candidate_count=1)
        self.assertNotIn('candidate_index', answer.changes)
        with self.assertRaises(PolicyExhausted):
            self.policy.reflect(r, self.parameters.updated({'time_scale': 3.}))

    def test_model_prompts_preserve_user_measurements_and_old_version(self):
        r = report(ErrorType.EMPTY_GRASP, grasp_residual_xy=[-.03, .02]).to_dict()
        history = [{'error': copy.deepcopy(r), 'reflection': {'cause': 'x', 'changes': {'time_scale': 1.5}}}]
        before = copy.deepcopy((r, history))
        kwargs = dict(parameters=self.parameters.to_dict(), history=history)
        old = messages('task', r, variant='flash_old', **kwargs)
        new = messages('task', r, variant='flash_new', **kwargs)
        self.assertEqual(original_messages('task', r, **kwargs), old)
        self.assertEqual(old[1:], new[1:])
        self.assertNotEqual(old[0]['content'], new[0]['content'])
        self.assertEqual(before, (r, history))

    def test_saved_pair_accepts_tuple_serialization_but_rejects_real_change(self):
        record = dict(parameters=self.parameters.to_dict(), accepted=False, physical_success=False,
                      error={'error_type': 'empty_grasp'}, evaluation={'position': [0., 0., 0.]},
                      candidate_trace={'initial_qpos': [0.], 'initial_body_xyz': [[0., 0., 0.]]})
        result = {'records': [record]}
        saved = json.loads(json.dumps(result))
        compare_saved(result, saved)
        saved['records'][0]['parameters']['lift_height'] = .45
        with self.assertRaises(AssertionError):
            compare_saved(result, saved)


if __name__ == '__main__':
    unittest.main()
