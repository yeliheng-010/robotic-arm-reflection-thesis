"""压缩冗长诊断，保留测量、参数和失败阶段，不生成修正答案。"""
import copy
import json
import os
import unittest
from reflection.reflector import Parameters


class PromptTests(unittest.TestCase):
    def test_project_error_preserves_actionable_measurements(self):
        report = {'error_type': 'collision', 'timestamp': 1, 'image_paths': ['x'], 'evidence': {
            'contacts': [['ur5e_base', 'SafetyDivider']], 'grasp_residual_xy': [.001, -.045],
            'contact_geometry': [{'bodies': ['table', 'object']}] * 100,
            'diagnostics': {'motion_segment': 'approach', 'grasp_filter': {
                'candidate_count': 90, 'collision_threshold': .01, 'collision_iou': [.001, .02] * 45}}}}
        before = copy.deepcopy(report)
        if os.environ.get('CHECK_LEGACY_PROMPT'):
            from training.refine.prompt import build_messages
        else:
            from stability.prompt import build_messages
        messages = build_messages('move object', report, parameters=Parameters().to_dict(),
            history=[{'error': report, 'reflection': {'cause': 'previous', 'changes': {'lift_height': .45}}}])
        value = json.loads(messages[1]['content'])
        evidence = value['error']['evidence']
        self.assertNotIn('contact_geometry', evidence)
        self.assertNotIn('collision_iou', evidence['diagnostics']['grasp_filter'])
        self.assertEqual([.001, -.045], evidence['grasp_residual_xy'])
        self.assertEqual('approach', evidence['diagnostics']['motion_segment'])
        self.assertEqual(report['evidence']['contacts'], evidence['contacts'])
        self.assertEqual(before, report)
        self.assertNotIn('collision_iou', messages[1]['content'])


if __name__ == '__main__':
    unittest.main()
