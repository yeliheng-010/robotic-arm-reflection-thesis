import unittest
from guard_policy import forbidden, release_reason


class ContactPolicyTests(unittest.TestCase):
    def test_arm_destination_is_not_exempt(self):
        self.assertTrue(forbidden(dict(roots=['ur5e_base', 'BlueBin'], geoms=['arm', 'wall']), 'RedBlock'))

    def test_gripper_destination_is_not_exempt(self):
        self.assertTrue(forbidden(dict(roots=['2f85_base', 'BlueBin'], geoms=['left_pad1', 'wall']), 'RedBlock'))

    def test_only_pads_may_touch_source(self):
        self.assertFalse(forbidden(dict(roots=['RedBlock', '2f85_base'], geoms=['block', 'right_pad2']), 'RedBlock'))
        self.assertTrue(forbidden(dict(roots=['RedBlock', '2f85_base'], geoms=['block', 'finger']), 'RedBlock'))
        self.assertTrue(forbidden(dict(roots=['ur5e_base', 'RedBlock'], geoms=['arm', 'block']), 'RedBlock'))

    def test_legacy_support_self_and_object_bin_are_preserved(self):
        for roots in (['ur5e_base', 'simple_table'], ['ur5e_base', '2f85_base'], ['RedBlock', 'BlueBin']):
            self.assertFalse(forbidden(dict(roots=roots, geoms=['a', 'b']), 'RedBlock'))

    def test_other_objects_still_forbidden(self):
        self.assertTrue(forbidden(dict(roots=['Knife', '2f85_base'], geoms=['knife', 'left_pad1']), 'RedBlock'))


class ReleasePolicyTests(unittest.TestCase):
    def evidence(self, **changes):
        return dict(held=True, actual=[0., 0., .89], expected=[0., 0., .86], **changes)

    def test_valid_release_and_boundary(self):
        self.assertIsNone(release_reason(self.evidence()))
        self.assertIsNone(release_reason(dict(held=True, actual=[.02, 0., .04], expected=[0., 0., 0.])))

    def test_no_hold_must_not_open(self):
        e = self.evidence()
        e['held'] = False
        self.assertEqual('object_dropped', release_reason(e))

    def test_large_actual_pose_error_must_not_open(self):
        for actual in ([.021, 0., .86], [0., 0., .901]):
            e = self.evidence()
            e['actual'] = actual
            self.assertEqual('placement_offset', release_reason(e))

    def test_nonfinite_is_rejected(self):
        e = self.evidence()
        e['actual'][0] = float('nan')
        self.assertEqual('placement_offset', release_reason(e))


if __name__ == '__main__':
    unittest.main()
