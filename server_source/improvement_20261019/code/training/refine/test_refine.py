"""证据与模型输出契约测试，不启动模型或物理仿真。"""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from reflection.reflector import Parameters
from training.refine.prompt import parse_response
from training.refine.instrumentation import TracedPlanner, filter_evidence, diagnostic_snapshot
from training.refine.runtime import final_answer
from training.refine.teacher_service import validate_request


class ResponseTests(unittest.TestCase):
    def test_teacher_rejects_nontext_or_wrong_role(self):
        for content, role in (({}, 'user'), ('x', 'assistant'), ('', 'user')):
            with self.subTest(content=content, role=role), self.assertRaises(ValueError):
                validate_request({'messages': [{'role': 'system', 'content': 'x'},
                                                {'role': role, 'content': content}]})

    def test_thinking_final_answer_is_separated_without_rewriting(self):
        answer = '{"cause":"measured","changes":{"replan":true}}'
        self.assertEqual(answer, final_answer('reasoning\n</think>\n' + answer, thinking=True))

    def test_incomplete_thinking_cannot_become_final_answer(self):
        with self.assertRaisesRegex(ValueError, 'before final answer'):
            final_answer('{"cause":"unfinished thought"}', thinking=True)

    def setUp(self):
        self.parameters = Parameters()

    def test_accepts_model_generated_correction_without_rewriting(self):
        raw = '{"cause":"Measured lateral residual","changes":{"grasp_offset":[0.0,0.04,0.0]}}'
        result = parse_response(raw, self.parameters)
        self.assertEqual({'grasp_offset': [0.0, 0.04, 0.0]}, result.changes)
        self.assertEqual('llm', result.source)

    def test_rejects_unsupported_measured_field(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            parse_response('{"cause":"test","changes":{"closure":0.5}}', self.parameters)

    def test_rejects_unchanged_parameters(self):
        with self.assertRaisesRegex(ValueError, 'does not change'):
            parse_response('{"cause":"test","changes":{"lift_height":0.35}}', self.parameters)

    def test_rejects_empty_changes(self):
        with self.assertRaisesRegex(ValueError, 'does not change'):
            parse_response('{"cause":"test","changes":{}}', self.parameters)

    def test_rejects_duplicate_json_fields(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            parse_response('{"cause":"a","cause":"b","changes":{"replan":true}}', self.parameters)

    def test_rejects_nonfinite_values(self):
        with self.assertRaises(ValueError):
            parse_response('{"cause":"test","changes":{"lift_height":NaN}}', self.parameters)

    def test_rejects_extra_objects(self):
        with self.assertRaises(ValueError):
            parse_response('{"cause":"test","changes":{"replan":true}} {}', self.parameters)

    def test_rejects_unknown_top_level_fields(self):
        with self.assertRaisesRegex(ValueError, 'cause and changes'):
            parse_response('{"cause":"test","changes":{"replan":true},"fault":"collision"}', self.parameters)

    def test_rejects_array_instead_of_object(self):
        with self.assertRaises(ValueError):
            parse_response('[]', self.parameters)


class EvidenceTests(unittest.TestCase):
    def test_capture_restores_functions_after_exception(self):
        from training.refine.instrumentation import capture, SEGMENTS
        original = lambda *a, **kw: None
        detector = SimpleNamespace(detect=original)
        flow = SimpleNamespace(**{name: original for name in SEGMENTS})
        monitor = SimpleNamespace(tick=original)
        grasp = SimpleNamespace(ModelFreeCollisionDetector=detector, GraspFlow=flow,
                                _run_planners=original)
        modules = {'grasp_process': grasp,
                   'reflection.monitors': SimpleNamespace(ExecutionMonitor=monitor)}
        with patch.dict('sys.modules', modules):
            with self.assertRaisesRegex(RuntimeError, 'abort'):
                with capture({}):
                    self.assertIsNot(original, detector.detect)
                    raise RuntimeError('abort')
        self.assertIs(original, detector.detect)
        self.assertIs(original, monitor.tick)
        self.assertIs(original, grasp._run_planners)
        for name in SEGMENTS:
            self.assertIs(original, getattr(flow, name))

    def test_joint_motion_does_not_retain_previous_cartesian_target(self):
        state = {'commanded_tcp_xyz': [1, 2, 3]}
        pose = [0.0] * 6
        wrapped = TracedPlanner(SimpleNamespace(interpolate=lambda t: pose),
                                state=state, segment='return_home')
        self.assertIs(pose, wrapped.interpolate(.1))
        self.assertNotIn('commanded_tcp_xyz', state)

    def test_placement_evaluation_separates_last_motion(self):
        state = {'action': 'back_to_zero', 'motion_segment': 'return_home',
                 'planner_calls': 2}
        result = diagnostic_snapshot(state, SimpleNamespace(stage='placement'))
        self.assertEqual('post_execution_evaluation', result['observation_phase'])
        self.assertEqual('return_home', result['last_completed_motion']['motion_segment'])
        self.assertNotIn('motion_segment', result)
        self.assertNotIn('planner_calls', result)
        self.assertEqual('return_home', state['motion_segment'])

    def test_filter_counts_overlap_once(self):
        result = filter_evidence([True, False, True], [False, True, True],
                                 ious=[[.02, 0, .03]], scene_points=80, threshold=.01)
        self.assertEqual(3, result['candidate_count'])
        self.assertEqual(2, result['collision_rejected'])
        self.assertEqual(2, result['empty_rejected'])
        self.assertEqual(0, result['surviving_count'])
        self.assertEqual([.02, 0, .03], result['collision_iou'])

    def test_filter_preserves_partial_survival(self):
        result = filter_evidence([False, True], [False, False],
                                 ious=[[0, .02]], scene_points=80, threshold=.01)
        self.assertEqual(1, result['surviving_count'])

    def test_planner_observation_returns_original_pose(self):
        class Coordinates(list):
            def tolist(self):
                return list(self)
        pose = SimpleNamespace(t=Coordinates([1.0, 0.2, 0.9]))
        planner = SimpleNamespace(interpolate=lambda t: pose)
        state = {}
        wrapped = TracedPlanner(planner, state=state, segment='transport')
        self.assertIs(pose, wrapped.interpolate(.2))
        self.assertEqual('transport', state['motion_segment'])
        self.assertEqual([1.0, .2, .9], state['commanded_tcp_xyz'])

    def test_planner_exception_is_not_swallowed(self):
        def fail(_):
            raise AssertionError('original failure')
        wrapped = TracedPlanner(SimpleNamespace(interpolate=fail), state={}, segment='lift')
        with self.assertRaisesRegex(AssertionError, 'original failure'):
            wrapped.interpolate(.1)


if __name__ == '__main__':
    unittest.main()

