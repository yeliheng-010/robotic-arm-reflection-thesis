import unittest
from contact_policy import forbidden


class ScopeTests(unittest.TestCase):
    def test_source_gripper_legacy_exception(self):
        for roots, geoms in ((['RedBlock', '2f85_base'], ['block', 'spring']),
                             (['2f85_base', 'RedBlock'], ['right_pad1', 'block'])):
            self.assertFalse(forbidden(dict(roots=roots, geoms=geoms), 'RedBlock'))

    def test_arm_source_is_still_forbidden(self):
        self.assertTrue(forbidden(dict(roots=['ur5e_base', 'RedBlock'], geoms=['arm', 'block']), 'RedBlock'))

    def test_all_robot_destination_contacts_are_forbidden(self):
        for root in ('ur5e_base', '2f85_base'):
            self.assertTrue(forbidden(dict(roots=[root, 'BlueBin'], geoms=['a', 'b']), 'RedBlock'))

    def test_object_destination_and_self_are_not_changed(self):
        for roots in (['RedBlock', 'BlueBin'], ['ur5e_base', '2f85_base']):
            self.assertFalse(forbidden(dict(roots=roots, geoms=['a', 'b']), 'RedBlock'))


if __name__ == '__main__':
    unittest.main()
