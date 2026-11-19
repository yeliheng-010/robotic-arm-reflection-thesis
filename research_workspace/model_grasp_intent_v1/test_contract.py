import unittest
from copy import deepcopy
from model_grasp_intent_v1.contract import validate_action


def intent(**changes):
    args = dict(region='center', depth_mm=30, tilt_deg=0, azimuth_deg=0, symmetry_deg=0)
    args.update(changes)
    return dict(id='PROPOSE_GRASP', args=args)


class ContractTests(unittest.TestCase):
    def test_model_can_choose_new_direction_and_depth(self):
        action = intent(region='long_positive', tilt_deg=60, azimuth_deg=270, depth_mm=15)
        self.assertEqual(action, validate_action(action))

    def test_invalid_fields_and_numbers_rejected(self):
        bad = [intent(tilt_deg=True), intent(depth_mm=float('nan')),
               intent(azimuth_deg=360), intent(region='RedBin'),
               intent(disable_collision=True), dict(id='EXECUTE', args={})]
        for action in bad:
            with self.subTest(action=action), self.assertRaises(ValueError):
                validate_action(action)

    def test_validation_returns_independent_copy(self):
        action = intent()
        result = validate_action(action)
        result['args']['depth_mm'] = 15
        self.assertEqual(30, action['args']['depth_mm'])

    def test_stop_and_observe_cannot_carry_hidden_arguments(self):
        for name in ('STOP', 'OBSERVE'):
            self.assertEqual(dict(id=name, args={}), validate_action(dict(id=name, args={})))
            with self.assertRaises(ValueError):
                validate_action(dict(id=name, args={'reason': 'private'}))
