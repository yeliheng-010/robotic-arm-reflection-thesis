import unittest
from route_audit_v2 import validate_rejection


class RejectionTests(unittest.TestCase):
    def test_raw_error_survives_projected_field_removal(self):
        record = dict(error={'evidence': {'route_planning_rejected': True}})
        step = dict(success=False, feedback={'evidence': {}})
        validate_rejection(record, step, guard={'open_called': False}, rows=[{'step': 0}])

    def test_missing_rejection_marker_is_not_certified(self):
        with self.assertRaises(KeyError):
            validate_rejection(dict(error={'evidence': {}}), dict(success=False),
                               guard={'open_called': False}, rows=[{'step': 0}])

    def test_physical_motion_is_not_zero_motion(self):
        with self.assertRaisesRegex(AssertionError, 'moved'):
            validate_rejection(dict(error={'evidence': {'route_planning_rejected': True}}),
                               dict(success=False), guard={'open_called': False}, rows=[{'step': 1}])


if __name__ == '__main__':
    unittest.main()
