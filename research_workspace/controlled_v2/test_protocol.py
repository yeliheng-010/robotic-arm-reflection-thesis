"""协议门禁：隔离因素、反馈旁路和正确分母。"""
import copy
import unittest
from controlled.config import tasks, scenario
from controlled.feedback import project_report
from controlled.metrics import summarize, paired_gains


class ProtocolTests(unittest.TestCase):
    def test_matrix_and_sealed_groups(self):
        self.assertEqual(48, len(tasks()))
        self.assertEqual(192, len(tasks(expanded=True)))
        sealed = {('PurpleCapsule', 'SortingTray'), ('OrangeSphere', 'RedBin')}
        self.assertFalse(any((t['source'], t['destination']) in sealed for t in tasks(expanded=True)))
        self.assertTrue(all(t['split'] == 'train' for t in tasks(expanded=True)))

    def test_component_randomness_is_independent(self):
        configs = {g: scenario(82000, g) for g in ('clean', 'layout', 'sensor', 'physics', 'feedback', 'mixed')}
        for group in ('sensor', 'feedback'):
            self.assertEqual(configs['clean']['bodies'], configs[group]['bodies'])
        for name in configs['clean']['bodies']:
            for key in ('xy', 'yaw_delta'):
                self.assertEqual(configs['layout']['bodies'][name][key], configs['mixed']['bodies'][name][key])
                self.assertEqual(configs['clean']['bodies'][name][key], configs['physics']['bodies'][name][key])
            for key in ('density_scale', 'friction_scale'):
                self.assertEqual(configs['physics']['bodies'][name][key], configs['mixed']['bodies'][name][key])
        self.assertEqual(configs['layout']['containers'], configs['mixed']['containers'])
        self.assertEqual(configs['sensor']['profile']['depth_sigma_m'], configs['mixed']['profile']['depth_sigma_m'])
        self.assertEqual(configs['feedback']['feedback'], configs['mixed']['feedback'])
        self.assertTrue(all(c['faults'] == configs['clean']['faults'] for c in configs.values()))

    def test_feedback_redacts_truth_and_preserves_source(self):
        report = dict(error_type='empty_grasp', stage='execution', message='secret xyz 1.234',
                      image_paths=['secret'], timestamp=123, evidence={
                          'grasp_residual_xy': [.04, -.01], 'position': [1.234, 2, 3],
                          'diagnostics': {'commanded_tcp_xyz': [1, 2, 3], 'available_candidate_count': 5}})
        before = copy.deepcopy(report)
        config = scenario(82000, 'feedback')
        config['feedback']['missing_probability'] = 0
        projected = project_report(report, config, attempt=1)
        self.assertEqual(before, report)
        self.assertNotIn('position', projected['evidence'])
        self.assertNotIn('commanded_tcp_xyz', projected['evidence']['diagnostics'])
        self.assertNotIn('secret', str(projected))
        self.assertNotEqual(report['evidence']['grasp_residual_xy'], projected['evidence']['grasp_residual_xy'])
        self.assertEqual(projected, project_report(report, config, attempt=1))
        self.assertNotEqual(projected, project_report(report, config, attempt=2))

    def test_missing_measurement_not_replaced_with_truth(self):
        report = dict(error_type='empty_grasp', stage='execution', evidence={'grasp_residual_xy': [.1, .2]})
        config = scenario(82000, 'feedback')
        config['feedback']['missing_probability'] = 1
        self.assertNotIn('grasp_residual_xy', project_report(report, config, attempt=1)['evidence'])

    def test_recovery_denominator_excludes_first_success(self):
        base = dict(arm='flash', task={'level': 'clean'}, attempts=1, calls=0,
                    invalid_outputs=0, service_errors=0, elapsed_s=1)
        rows = [dict(base, first_success=True, success=True),
                dict(base, first_success=False, success=True),
                dict(base, first_success=False, success=False, service_errors=1)]
        metrics = summarize(rows)['clean']['flash']
        self.assertEqual(3, metrics['tasks'])
        self.assertEqual(2, metrics['first_failures'])
        self.assertEqual(1, metrics['recoveries'])
        self.assertEqual(.5, metrics['recovery_rate'])
        self.assertEqual(0, metrics['invalid_outputs'])
        self.assertEqual(1, metrics['service_errors'])

    def test_paired_gain_uses_matching_cases_only(self):
        rows = [dict(case=0, arm='retry', success=False, task={'level': 'clean'}),
                dict(case=0, arm='flash', success=True, task={'level': 'clean'}),
                dict(case=1, arm='flash', success=False, task={'level': 'clean'})]
        paired = paired_gains(rows)['clean']['flash']
        self.assertEqual(1, paired['pairs'])
        self.assertEqual(1, paired['success_gain'])


if __name__ == '__main__':
    unittest.main()
