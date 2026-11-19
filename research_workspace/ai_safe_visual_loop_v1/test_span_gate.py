import unittest
from copy import deepcopy
from unittest.mock import patch
from prepare_v3 import validate_recovery, qualified_cases, LIFT_M


class SpanGateTests(unittest.TestCase):
    def test_initial_success_and_engineering_recovery_cannot_open_gate(self):
        zero = dict(summary=dict(verified_natural_recoveries=0), rows=[])
        with self.assertRaises(AssertionError):
            validate_recovery(zero)
        row = dict(eligible_natural=False, verified_recovery=True, snapshot_id='x',
            before=dict(success=False), successor=dict(success=True))
        value = dict(summary=dict(verified_natural_recoveries=1), rows=[row])
        with self.assertRaises(AssertionError):
            validate_recovery(value)
        row['eligible_natural'] = True
        validate_recovery(value)
        row['before']['success'] = True
        with self.assertRaises(AssertionError):
            validate_recovery(value)

    def test_preparation_uses_new_lift_without_mutating_reservation(self):
        from sv_common import ROOT, read
        reserved = read(ROOT.parent/'safe_visual_qualification_v2/manifest.json')
        result = read(ROOT.parent/'safe_visual_qualification_v2/result.json')
        snapshot = deepcopy(reserved)
        cases = qualified_cases(reserved, result)
        self.assertEqual(snapshot, reserved)
        self.assertEqual(sum(r['passed'] for r in result['rows']), len(cases))
        for case in cases:
            self.assertEqual(LIFT_M, case['state']['parameters']['lift_height'])
            self.assertEqual(dict(grasp_mode='world_down'), case['control'])


if __name__ == '__main__':
    unittest.main()
