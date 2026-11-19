import json
import unittest
from tracking_facts import summarize


def row(time=1., **extra):
    return dict(time_s=time, action='close_gripper', command_tcp_xyz_m=[0.,0.,0.],
                tcp_fk_xyz_m=[.03,.04,0.], gripper_joint_rad=.2, **extra)


class TrackingTests(unittest.TestCase):
    def test_physical_units_and_measured_closure(self):
        first, last = row(), row(2.)
        last['gripper_joint_rad'] = .6
        value = summarize([first, last])['actions'][0]
        self.assertAlmostEqual(.05, value['last']['position_error_m'])
        self.assertAlmostEqual(.4, value['gripper_joint_change_rad'])

    def test_private_fields_never_copied(self):
        value = summarize([row(error_type='secret', root_cause='hidden', success=True, source_xyz=[9,9,9])])
        text = json.dumps(value)
        for forbidden in ('secret','hidden','root_cause','source_xyz','success'):
            self.assertNotIn(forbidden, text)

    def test_invalid_or_out_of_order_rejected(self):
        bad = row()
        bad['tcp_fk_xyz_m'] = [float('nan'),0,0]
        with self.assertRaises(ValueError):
            summarize([bad])
        with self.assertRaises(ValueError):
            summarize([row(2.),row(1.)])

    def test_empty_is_missing_not_success(self):
        self.assertEqual([], summarize([])['actions'])


if __name__ == '__main__':
    unittest.main()
