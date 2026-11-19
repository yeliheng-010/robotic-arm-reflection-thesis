import unittest
from camera_registration import configuration


def case(group, camera):
    return dict(item=dict(seed=42,group=group),config=dict(group=group,camera=camera))


class RegistrationTests(unittest.TestCase):
    def test_baseline_first_does_not_select_missing_camera(self):
        selected = configuration([case('baseline',None),case('varied_noisy',{'pose':1})],42)
        self.assertEqual({'pose':1},selected['camera'])
        self.assertEqual('varied_noisy',selected['group'])

    def test_missing_varied_camera_does_not_fall_back(self):
        with self.assertRaises(ValueError):
            configuration([case('baseline',None)],42)

    def test_conflicting_same_seed_configs_are_rejected(self):
        with self.assertRaises(ValueError):
            configuration([case('varied_noisy',{'pose':1}),case('varied_noisy',{'pose':2})],42)


if __name__=='__main__':
    unittest.main(verbosity=2)
